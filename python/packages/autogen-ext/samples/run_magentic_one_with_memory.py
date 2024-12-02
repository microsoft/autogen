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

PATH_TO_ARCHIVE_DIR = "~/agentic_memory_archive"


def define_tasks_with_answers():
    tasks_with_answers = []

    # Task index 0
    tasks_with_answers.append({
        "task": """You ask 100 people: 'How many of you are liars?' They all answer: 'At least one of us is not a liar.' But you know that at least one of the 100 is a liar. How many of them are liars? 

The final line of your response must contain nothing but the answer as a number.""",
        "expected_answer": "100"})

    # Task index 1
    tasks_with_answers.append({
        "task": """You are Van Helsing, a renowned vampire hunter. A Count of Moldova, La\u021bcu IV, son of  Costea, has tasked you with investigating the village of \u0218irnea in neighboring Wallachia. The Count's advisors have reported that a vampire was spotted crossing the border near the village, and would like you to investigate it.

You travel to the village of \u0218irnea, and you begin your investigation. One night, just before dawn, you catch a glimpse of a man in a long black cape with red lining leaping from roof-top to roof-top with superhuman agility. It's a vampire! You try to chase the creature back to its home, but the creature is too fast. However, because of the remoteness of the village, you know with absolute certainty that the vampire must be a resident of the village. You decide that your best course of action will be to visit all 100 residents of the town during the day. You know something about vampires and humans that will make your investigation possible; humans always tell the truth, but vampires always lie.

In the afternoon, you go from house to house, speaking with all 100 residents of \u0218irnea. You ask everyone the same question: \"How many vampires are living in \u0218irnea\". Everyone in the village gives the same response, \"At least one of us is a human.\"\n\nHow many residents of \u0218irnea have been turned into vampires?

The final line of your response must contain nothing but the answer as a number.""",
        "expected_answer": "100"})

    # Task index 2
    tasks_with_answers.append({
        "task": """Three guards stand at a door. You need to determine how many of them are truthful, and you already know that one of them is not. You ask each one 'How many guards here tell the truth?' Each one says 'One or more of us always tells the truth'. How many of the guards tell the truth?

The final line of your response must contain nothing but the answer as a number.""",
        "expected_answer": "3"})

    return tasks_with_answers


def create_client():
    # Create an OpenAI client
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
    return client


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
    page = page_log.begin_page(
        summary="assign_task_to_client",
        details='',
        method_call="assign_task_to_client")

    page.add_lines(task)

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

    page_log.finish_page(page)
    return answer, response.content


async def train(task_with_answer, max_train_trials, max_test_trials, task_assignment_callback, reset_memory,
                client, page_log) -> None:
    memory = AgenticMemory(reset=reset_memory, client=client, page_log=page_log, path_to_archive_dir=PATH_TO_ARCHIVE_DIR)
    await memory.train_on_task(
        task=task_with_answer["task"],
        expected_answer=task_with_answer["expected_answer"],
        task_assignment_callback=task_assignment_callback,
        final_format_instructions="",
        max_train_trials=max_train_trials,
        max_test_trials=max_test_trials)


async def test(task_with_answer, num_trials, task_assignment_callback, reset_memory,
               client, page_log) -> Tuple[str, int, int]:
    memory = AgenticMemory(reset=reset_memory, client=client, page_log=page_log, path_to_archive_dir=PATH_TO_ARCHIVE_DIR)
    response, num_successes, num_trials = await memory.test_on_task(
        task=task_with_answer["task"],
        expected_answer=task_with_answer["expected_answer"],
        task_assignment_callback=task_assignment_callback,
        num_trials=num_trials)
    return response, num_successes, num_trials


async def train_and_test(task_index, max_train_trials, max_test_trials, task_assignment_callback, page_log):
    tasklist = define_tasks_with_answers()
    task_with_answer = tasklist[task_index]

    num_loops = 10
    total_num_successes = 0
    total_num_trials = 0
    for i in range(num_loops):
        await train(
            task_with_answer=task_with_answer,
            max_train_trials=max_train_trials,
            max_test_trials=max_test_trials,
            task_assignment_callback=task_assignment_callback,
            reset_memory=True,
            client=create_client(),
            page_log=page_log)
        last_response, num_successes, num_trials = await test(
            task_with_answer=task_with_answer,
            num_trials=max_test_trials,
            task_assignment_callback=task_assignment_callback,
            reset_memory=False,
            client=create_client(),
            page_log=page_log)
        print("SUCCESS RATE:  {}%\n".format(round((num_successes / num_trials) * 100)))
        total_num_successes += num_successes
        total_num_trials += num_trials
    return total_num_successes, total_num_trials


async def test_on_task_with_memory(task_index, task_assignment_callback, page_log, num_trials, reset_memory):
    last_response, num_successes, num_trials = await test(
        task_with_answer=define_tasks_with_answers()[task_index],
        num_trials=num_trials,
        task_assignment_callback=task_assignment_callback,
        reset_memory=reset_memory,
        client=create_client(),
        page_log=page_log)
    print("SUCCESS RATE:  {}%\n".format(round((num_successes / num_trials) * 100)))


async def main() -> None:
    # Create the PageLog. (This is optional)
    page_log = PageLog("~/pagelogs/", "code_sample")
    page = page_log.begin_page(
        summary="main",
        details='',
        method_call="main")

    task_index = 1
    task_assignment_callback = assign_task_to_magentic_one  # assign_task_to_client or assign_task_to_magentic_one

    # await test_on_task_with_memory(task_index, task_assignment_callback, page_log, num_trials=3, reset_memory=True)

    num_successes, num_trials = await train_and_test(task_index, 10, 3, task_assignment_callback, page_log)
    success_rate = round((num_successes / num_trials) * 100)
    page.add_lines("\nOverall success rate:  {}%\n".format(success_rate), flush=True)

    page_log.flush(final=True)  # Finalize the page log
    page_log.finish_page(page)

if __name__ == "__main__":
    # logger = logging.getLogger(EVENT_LOGGER_NAME)
    # logger.setLevel(logging.INFO)
    # log_handler = LogHandler()
    # logger.handlers = [log_handler]
    asyncio.run(main())
