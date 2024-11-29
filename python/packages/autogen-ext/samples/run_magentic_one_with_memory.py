import asyncio
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents import MultimodalWebSurfer
from autogen_ext.agents.web_surfer._utils import message_content_to_str
from autogen_agentchat.task import Console
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from typing import (
    Tuple,
)
from autogen_ext.agentic_memory import AgenticMemory, PageLog


USE_AGENTIC_MEMORY = 1  # 1 = Assign task to AgenticMemory instead of directly to the completion agent
CREATE_NEW_MEMORIES = 1  # 1 = Let AgenticMemory try to create new memories
RESET_MEMORY = 1  # 1 = Reset the memory before starting each task


async def assign_task_to_magentic_one(task, model_client, page_log) -> Tuple[str, str]:
    page = page_log.begin_page(
        summary="assign_task_to_magentic_one",
        details='',
        method_call="assign_task_to_magentic_one")

    page.add_lines(task)

    general_agent = AssistantAgent(
        "general_agent",
        model_client,
        description="A general GPT-4o AI assistant capable of performing a variety of tasks.", )

    web_surfer = MultimodalWebSurfer(
        name="web_surfer",
        model_client=model_client,
        downloads_folder="logs",
        debug_dir="logs",
        to_save_screenshots=True,
    )

    team = MagenticOneGroupChat(
        [general_agent, web_surfer],
        model_client=model_client,
        max_turns=20,
    )

    # user_input = await asyncio.get_event_loop().run_in_executor(None, input, ">: ")
    stream = team.run_stream(task=task)
    task_result = await Console(stream)

    # Use the entire task_result (with images removed) as the work history.
    work_history = "\n".join([message_content_to_str(message.content) for message in task_result.messages])

    # Extract the final response as the last line of the last message.
    # This assumes that the task statement specified that the answer should be on the last line.
    final_message_string = task_result.messages[-1].content
    final_message_lines = final_message_string.split("\n")
    final_response = final_message_lines[-1]

    page_log.finish_page(page)

    return final_response, work_history


async def assign_task_to_client(task, client, page_log):
    # The client is a ChatCompletionClient. Pass the task to it, and return the response.
    system_message = SystemMessage(content="""You are a helpful and thoughtful assistant.
In responding to every user message, you follow the same multi-step process given here:
1. Explain your understanding of the user message in detail, covering all the important points.
2. List as many possible responses as you can think of.
3. Carefully list and weigh the pros and cons (if any) of each possible response.
4. Critique the pros and cons above, looking for any flaws in your reasoning. But don't make up flaws that don't exist.
5. Decide on the best response, looping back to step 1 if none of the responses are satisfactory.
6. Finish by providing your final response in the particular format requested by the user.""")
    user_message = UserMessage(content=task, source="human")

    input_messages = [system_message] + [user_message]
    response = await client.create(input_messages)

    # Log the model call
    page_log.add_model_call(description="Ask the model",
                            details="to complete the task", input_messages=input_messages,
                            response=response,
                            num_input_tokens=0, caller='assign_task_to_client')

    # Split the response into lines.
    response_lines = response.content.split("\n")

    # The final line contains the answer. Extract it.
    answer = response_lines[-1]

    return answer, response.content


async def task_assignment_callback(task, client, page_log) -> str:
    page = page_log.begin_page(
        summary="task_assignment_callback",
        details='',
        method_call="task_assignment_callback")

    # Send the task to an agent, team or client.
    # response, work_history = await assign_task_to_client(task.strip(), client, page_log)
    response, work_history = await assign_task_to_magentic_one(task.strip(), client, page_log)

    page.update_details("  " + response)
    page_log.finish_page(page)
    return response, work_history


async def main() -> None:
    # Select the task
    task = """You ask 100 people: 'How many of you are liars?' They all answer: 'At least one of us is not a liar.' But you know that at least one of the 100 is a liar. How many of them are liars? The final line of your response must contain nothing but the answer as a number."""
    expected_answer = "100"

    # Create the OpenAI client
    model_name = "gpt-4o-2024-05-13"
    temp = 0.1
    max_tokens = 4096
    client = OpenAIChatCompletionClient(
        model=model_name,
        api_key="",
        temperature=temp,
        max_tokens=max_tokens,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        top_p=1.0,
        max_retries=65535,
    )

    # Create the PageLog.
    page_log = PageLog("~/pagelogs/", "m1")
    page = page_log.begin_page(
        summary="main",
        details='',
        method_call="main")
    page_log.append_entry_line(f"Using  {model_name} on OAI, temp={temp}, max_tokens={max_tokens}")

    if USE_AGENTIC_MEMORY:
        memory = AgenticMemory(reset=RESET_MEMORY, client=client, page_log=page_log, path_to_archive_dir="~/agentic_memory_archive")
        prepared_response = await memory.assign_task(
            task, expected_answer, CREATE_NEW_MEMORIES, task_assignment_callback, final_format_instructions="")
    else:
        prepared_response, _ = await task_assignment_callback(task, client, page_log)

    print("FINAL RESPONSE AFTER LEARNING:  ", prepared_response)
    page.add_lines(prepared_response)
    page_log.flush(final=True)  # Finalize the page log
    page_log.finish_page(page)

if __name__ == "__main__":
    # logger = logging.getLogger(EVENT_LOGGER_NAME)
    # logger.setLevel(logging.INFO)
    # log_handler = LogHandler()
    # logger.handlers = [log_handler]
    asyncio.run(main())
