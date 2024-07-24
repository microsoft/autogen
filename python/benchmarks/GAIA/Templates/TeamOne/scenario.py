import asyncio
import logging
import os

from typing import List
from agnext.application import SingleThreadedAgentRuntime
from agnext.application.logging import EVENT_LOGGER_NAME
from agnext.components.models import (
    AzureOpenAIChatCompletionClient,
    ChatCompletionClient,
    ModelCapabilities,
    UserMessage,
    LLMMessage,
)
from agnext.components.code_executor import LocalCommandLineCodeExecutor
from agnext.application.logging import EVENT_LOGGER_NAME
from team_one.markdown_browser import MarkdownConverter, UnsupportedFormatException
from team_one.agents.coder import Coder, Executor
from team_one.agents.orchestrator import LedgerOrchestrator
from team_one.messages import BroadcastMessage
from team_one.agents.multimodal_web_surfer import MultimodalWebSurfer
from team_one.agents.file_surfer import FileSurfer
from team_one.utils import LogHandler, message_content_to_str

import re

from agnext.components.models import AssistantMessage


async def response_preparer(task: str, source: str, client: ChatCompletionClient, transcript: List[LLMMessage]) -> str:
    messages: List[LLMMessage] = [
        UserMessage(
            content=f"Earlier you were asked the following:\n\n{task}\n\nYour team then worked diligently to address that request. Here is a transcript of that conversation:",
            source=source,
        )
    ]

    # copy them to this context
    for message in transcript:
        messages.append(
            UserMessage(
                content = message_content_to_str(message.content),
                # TODO fix this -> remove type ignore
                source=message.source, # type: ignore
            )
        )

    # ask for the final answer
    messages.append(
        UserMessage(
            content= f"""
Read the above conversation and output a FINAL ANSWER to the question. The question is repeated here for convenience:

{task}

To output the final answer, use the following template: FINAL ANSWER: [YOUR FINAL ANSWER]
Your FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.
ADDITIONALLY, your FINAL ANSWER MUST adhere to any formatting instructions specified in the original question (e.g., alphabetization, sequencing, units, rounding, decimal places, etc.)
If you are asked for a number, express it numerically (i.e., with digits rather than words), don't use commas, and don't include units such as $ or percent signs unless specified otherwise.
If you are asked for a string, don't use articles or abbreviations (e.g. for cities), unless specified otherwise. Don't output any final sentence punctuation such as '.', '!', or '?'.
If you are asked for a comma separated list, apply the above rules depending on whether the elements are numbers or strings.
""",
#If you are unable to determine the final answer, output 'FINAL ANSWER: Unable to determine'
            source=source,
        )
    )


    response = await client.create(messages)
    assert isinstance(response.content, str)

    # No answer
    if "unable to determine" in response.content.lower():
        messages.append( AssistantMessage(content=response.content, source="self" ) )
        messages.append(
            UserMessage(
                content= f"""
I understand that a definitive answer could not be determined. Please make a well-informed EDUCATED GUESS based on the conversation.

To output the educated guess, use the following template: EDUCATED GUESS: [YOUR EDUCATED GUESS]
Your EDUCATED GUESS should be a number OR as few words as possible OR a comma separated list of numbers and/or strings. DO NOT OUTPUT 'I don't know', 'Unable to determine', etc.
ADDITIONALLY, your EDUCATED GUESS MUST adhere to any formatting instructions specified in the original question (e.g., alphabetization, sequencing, units, rounding, decimal places, etc.)
If you are asked for a number, express it numerically (i.e., with digits rather than words), don't use commas, and don't include units such as $ or percent signs unless specified otherwise.
If you are asked for a string, don't use articles or abbreviations (e.g. for cities), unless specified otherwise. Don't output any final sentence punctuation such as '.', '!', or '?'.
If you are asked for a comma separated list, apply the above rules depending on whether the elements are numbers or strings.
""".strip(),
                source=source,
            )
        )

        response = await client.create(messages)
        assert isinstance(response.content, str)
        return re.sub(r"EDUCATED GUESS:", "FINAL ANSWER:", response.content)

    else:
        return response.content


async def main() -> None:
    # Read the prompt
    prompt = ""
    with open("prompt.txt", "rt") as fh:
        prompt = fh.read().strip()
    filename = "__FILE_NAME__".strip()

    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Create the AzureOpenAI client, with AAD auth
    # token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAIChatCompletionClient(
        api_version="2024-02-15-preview",
        azure_endpoint="https://aif-complex-tasks-west-us-3.openai.azure.com/",
        model="gpt-4o-2024-05-13",
        model_capabilities=ModelCapabilities(
            function_calling=True, json_output=True, vision=True
        ),
        # azure_ad_token_provider=token_provider
    )

    # Register agents.
    coder = await runtime.register_and_get_proxy(
        "Coder",
        lambda: Coder(model_client=client),
    )

    executor = await runtime.register_and_get_proxy(
        "Executor",
        lambda: Executor(
            "A agent for executing code", executor=LocalCommandLineCodeExecutor()
        ),
    )

    file_surfer = await runtime.register_and_get_proxy(
        "file_surfer",
        lambda: FileSurfer(model_client=client),
    )

    web_surfer = await runtime.register_and_get_proxy(
        "WebSurfer",
        lambda: MultimodalWebSurfer(), # Configuration is set later by init()
    )

    orchestrator = await runtime.register_and_get_proxy("orchestrator", lambda: LedgerOrchestrator(
        agents=[coder, executor, file_surfer, web_surfer],
        model_client=client,
    ))

    run_context = runtime.start()

    actual_surfer = await runtime.try_get_underlying_agent_instance(web_surfer.id, type=MultimodalWebSurfer)  
    await actual_surfer.init(model_client=client, downloads_folder=os.getcwd(), browser_channel="chromium")

    #await runtime.send_message(RequestReplyMessage(), user_proxy.id)

    filename_prompt = ""
    if len(filename) > 0:
        #relpath = os.path.join("coding", filename)
        #file_uri = pathlib.Path(os.path.abspath(os.path.expanduser(relpath))).as_uri()

        filename_prompt = f"The question is about a file, document or image, which can be accessed by the filename '{filename}' in the current working directory."

        try:
            mdconverter = MarkdownConverter()
            res = mdconverter.convert(filename)
            if res.text_content:
                #if count_token(res.text_content) < 8000:  # Don't put overly-large documents into the prompt
                filename_prompt += "\n\nHere are the file's contents:\n\n" + res.text_content
        except UnsupportedFormatException:
            pass

        #mdconverter = MarkdownConverter(mlm_client=client)
        #mlm_prompt = f"""Write a detailed caption for this image. Pay special attention to any details that might be useful for someone answering the following:

#{PROMPT}
#""".strip()

    task = f"{prompt}\n\n{filename_prompt}"

    await runtime.publish_message(
        BroadcastMessage(content=UserMessage(content=task.strip(), source="human")),
        namespace="default",
    )

    await run_context.stop_when_idle()

    # Output the final answer
    actual_orchestrator = await runtime.try_get_underlying_agent_instance(orchestrator.id, type=LedgerOrchestrator)
    transcript: List[LLMMessage] = actual_orchestrator._chat_history # type: ignore
    print(await response_preparer(task=task, source=(await orchestrator.metadata)["name"], client=client, transcript=transcript))



if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
