import asyncio
import logging
import os
import re
import tiktoken

from openai import AzureOpenAI

from typing import List

from autogen_core import AgentId, AgentProxy, TopicId
from autogen_core import SingleThreadedAgentRuntime
from autogen_core.logging import EVENT_LOGGER_NAME
from autogen_core.models import (
    ChatCompletionClient,
    UserMessage,
    LLMMessage,
)
from autogen_core import DefaultSubscription, DefaultTopicId
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_core.models import AssistantMessage

from autogen_magentic_one.markdown_browser import MarkdownConverter, UnsupportedFormatException
from autogen_magentic_one.agents.coder import Coder, Executor
from autogen_magentic_one.agents.orchestrator import LedgerOrchestrator
from autogen_magentic_one.messages import BroadcastMessage
from autogen_magentic_one.agents.multimodal_web_surfer import MultimodalWebSurfer
from autogen_magentic_one.agents.file_surfer import FileSurfer
from autogen_magentic_one.utils import LogHandler, message_content_to_str, create_completion_client_from_env

encoding = None
def count_token(value: str) -> int:
    # TODO:: Migrate to model_client.count_tokens
    global encoding
    if encoding is None:
        encoding = tiktoken.encoding_for_model("gpt-4o-2024-05-13")
    return len(encoding.encode(value))

async def response_preparer(task: str, source: str, client: ChatCompletionClient, transcript: List[LLMMessage]) -> str:
    messages: List[LLMMessage] = []

    # copy them to this context
    for message in transcript:
        messages.append(
            UserMessage(
                content = message_content_to_str(message.content),
                # TODO fix this -> remove type ignore
                source=message.source, # type: ignore
            )
        )

    # Remove messages until we are within 2k of the context window limit
    while len(messages) and client.remaining_tokens( messages ) < 2000:
        messages.pop(0)

    # Add the preamble
    messages.insert(0,
        UserMessage(
            content=f"Earlier you were asked the following:\n\n{task}\n\nYour team then worked diligently to address that request. Here is a transcript of that conversation:",
            source=source,
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
If you are unable to determine the final answer, output 'FINAL ANSWER: Unable to determine'
""",
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

    # Create the AzureOpenAI client from the environment file
    client = create_completion_client_from_env()


    mlm_client = create_completion_client_from_env()


    # Register agents.
    await runtime.register(
        "Assistant",
        lambda: Coder(model_client=client),
        subscriptions=lambda: [DefaultSubscription()],
    )
    coder = AgentProxy(AgentId("Assistant", "default"), runtime)

    await runtime.register(
        "ComputerTerminal",
        lambda: Executor(executor=LocalCommandLineCodeExecutor(), confirm_execution="ACCEPT_ALL"),
        subscriptions=lambda: [DefaultSubscription()],
    )
    executor = AgentProxy(AgentId("ComputerTerminal", "default"), runtime)

    await runtime.register(
        "FileSurfer",
        lambda: FileSurfer(model_client=client),
        subscriptions=lambda: [DefaultSubscription()],
    )
    file_surfer = AgentProxy(AgentId("FileSurfer", "default"), runtime)

    await runtime.register(
        "WebSurfer",
        lambda: MultimodalWebSurfer(), # Configuration is set later by init()
        subscriptions=lambda: [DefaultSubscription()],
    )
    web_surfer = AgentProxy(AgentId("WebSurfer", "default"), runtime)

    await runtime.register("Orchestrator", lambda: LedgerOrchestrator(
            agents=[coder, executor, file_surfer, web_surfer],
            model_client=client,
            max_rounds=30,
            max_time=25*60,
        ),
        subscriptions=lambda: [DefaultSubscription()],
    )
    orchestrator = AgentProxy(AgentId("Orchestrator", "default"), runtime)

    runtime.start()

    actual_surfer = await runtime.try_get_underlying_agent_instance(web_surfer.id, type=MultimodalWebSurfer)
    await actual_surfer.init(model_client=client, downloads_folder=os.getcwd(), browser_channel="chromium")

    filename_prompt = ""
    if len(filename) > 0:
        #relpath = os.path.join("coding", filename)
        #file_uri = pathlib.Path(os.path.abspath(os.path.expanduser(relpath))).as_uri()

        filename_prompt = f"The question is about a file, document or image, which can be accessed by the filename '{filename}' in the current working directory."

        mlm_prompt = f"""Write a detailed caption for this image. Pay special attention to any details that might be useful for someone answering the following:

{prompt}
""".strip()

        try:
            mdconverter = MarkdownConverter(mlm_client=mlm_client, mlm_model="gpt-4o-2024-05-13")
            res = mdconverter.convert(filename, mlm_prompt=mlm_prompt)
            if res.text_content:
                if count_token(res.text_content) < 8000:  # Don't put overly-large documents into the prompt
                    filename_prompt += "\n\nHere are the file's contents:\n\n" + res.text_content
        except UnsupportedFormatException:
            pass

    task = f"{prompt}\n\n{filename_prompt}"

    await runtime.publish_message(
        BroadcastMessage(content=UserMessage(content=task.strip(), source="human")),
        topic_id=DefaultTopicId(),
    )

    await runtime.stop_when_idle()

    # Output the final answer
    actual_orchestrator = await runtime.try_get_underlying_agent_instance(orchestrator.id, type=LedgerOrchestrator)
    transcript: List[LLMMessage] = actual_orchestrator._chat_history # type: ignore
    print(await response_preparer(task=task, source=(await orchestrator.metadata)["type"], client=client, transcript=transcript))


if __name__ == "__main__":
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    log_handler = LogHandler()
    logger.handlers = [log_handler]
    asyncio.run(main())
