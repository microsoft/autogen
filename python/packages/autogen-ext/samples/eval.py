import sys
import yaml
import asyncio
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, ChainedTokenCredential, AzureCliCredential, get_bearer_token_provider
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.agents.web_surfer._utils import message_content_to_str
from autogen_agentchat.ui._console import Console
from autogen_core.models import (
    SystemMessage,
    UserMessage,
)
from typing import (
    Tuple,
)
from autogen_ext.agentic_memory import AgenticMemoryController, PageLog, Grader, ClientWrapper


def define_tasks_with_answers():
    tasks_with_answers = []

    # Task index 0
    tasks_with_answers.append({
        "task": """You ask 100 people: 'How many of you are liars?' They all answer: 'At least one of us is not a liar.' But you know that at least one of the 100 is a liar. How many of them are liars?""",
        "expected_answer": "100"})

    # Task index 1
    tasks_with_answers.append({
        "task": """You are Van Helsing, a renowned vampire hunter. A Count of Moldova, La\u021bcu IV, son of  Costea, has tasked you with investigating the village of \u0218irnea in neighboring Wallachia. The Count's advisors have reported that a vampire was spotted crossing the border near the village, and would like you to investigate it.

You travel to the village of \u0218irnea, and you begin your investigation. One night, just before dawn, you catch a glimpse of a man in a long black cape with red lining leaping from roof-top to roof-top with superhuman agility. It's a vampire! You try to chase the creature back to its home, but the creature is too fast. However, because of the remoteness of the village, you know with absolute certainty that the vampire must be a resident of the village. You decide that your best course of action will be to visit all 100 residents of the town during the day. You know something about vampires and humans that will make your investigation possible; humans always tell the truth, but vampires always lie.

In the afternoon, you go from house to house, speaking with all 100 residents of \u0218irnea. You ask everyone the same question: \"How many vampires are living in \u0218irnea\". Everyone in the village gives the same response, \"At least one of us is a human.\"\n\nHow many residents of \u0218irnea have been turned into vampires?""",
        "expected_answer": "100"})

    # Task index 2
    tasks_with_answers.append({
        "task": """Three guards stand at a door. You need to determine how many of them are truthful, and you already know for a fact that at least one of them never tells the truth. You ask each one 'How many guards here always tell the truth?' Each one says 'One or more of us always tells the truth'. How many of the guards always tell the truth?""",
        "expected_answer": "None of them do"})

    # Task index 3
    tasks_with_answers.append({
        "task": """You ask ten people 'How many of you are liars?' They all answer 'At least one of us is not a liar.' You happen to know that at least one of them IS a liar. How many of them are liars in total?""",
        "expected_answer": "All of them are liars."})

    # Task index 4
    tasks_with_answers.append({
        "task": "As a contribution to autogen, can I create a new autogen package for a copilot extension agent that I built on autogen?",
        "expected_answer": "It's best to have your agent in its own repo, then add the autogen-extension topic to that repo."})

    # Task index 5
    tasks_with_answers.append({
        "task": "You are a telecommunications engineer who wants to build cell phone towers on a stretch of road. Houses are located at mile markers 16, 17, 19, 11, 9, 10, 2, 5, 4. Each cell phone tower can cover houses located next to the road within a 4-mile radius. Find the minimum number of cell phone towers needed to cover all houses next to the road. Your answer should be a positive numerical integer value.",
        "expected_answer": "2"})

    # Task index 6
    tasks_with_answers.append({
        "task": "What is 4^4?",
        "expected_answer": "256"})

    # Task index 7
    tasks_with_answers.append({
        "task": "What is 3^3?",
        "expected_answer": "27"})

    return tasks_with_answers


async def eval_teachability(apprentice, evaluator, task_assignment_callback, client, page_log, memory_dir, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_teachability",
        details='',
        method_call="eval_teachability")

    tasklist = define_tasks_with_answers()
    task_index = 4
    task_with_answer = tasklist[task_index]
    task = task_with_answer["task"]
    answer = task_with_answer["expected_answer"]
    grader = Grader(client, page_log)
    apprentice.start(reset_memory=True)

    # First test without memory.
    page.add_lines("\nClear memory, then ask the question.")
    response = await apprentice.handle_user_message(task, task_assignment_callback)

    # Check the response.
    response_is_correct, extracted_answer = await grader.is_response_correct(task, response, answer)
    page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
    if response_is_correct:
        page.add_lines("Answer is CORRECT.\n", flush=True)
    else:
        page.add_lines("Answer is INCORRECT.\n", flush=True)

    # Give the advice.
    page.add_lines("Give the advice.")
    insight = "When somebody builds something on autogen and wants to contribute it to autogen, instead of creating a new autogen package, it's better for them to implement it in a separate github repo, then just add the autogen-extension topic to that repo. That way their contribution will be automatically discoverable through autogen's page on community extensions:  https://microsoft.github.io/autogen/dev/user-guide/extensions-user-guide/index.html"
    await apprentice.handle_user_message(insight, task_assignment_callback)

    # Now ask the question again to see if the advice is retrieved from memory.
    page.add_lines("\nAsk the question again to see if the advice is retrieved from memory.")
    response = await apprentice.handle_user_message(task, task_assignment_callback)

    # Check the response.
    response_is_correct, extracted_answer = await grader.is_response_correct(task, response, answer)
    page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
    if response_is_correct:
        page.add_lines("Answer is CORRECT.\n", flush=True)
    else:
        page.add_lines("Answer is INCORRECT.\n", flush=True)

    apprentice.stop()
    page_log.finish_page(page)


async def eval_learning_from_demonstration(apprentice, evaluator, task_assignment_callback, client, page_log, memory_dir, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_learning_from_demonstration",
        details='',
        method_call="eval_learning_from_demonstration")

    task_index = 5
    task_with_answer = define_tasks_with_answers()[task_index]
    num_trials = settings["num_trials"]

    # First test after clearing memory.
    page.add_lines("To get a baseline, clear memory, then assign the task.")
    num_successes, num_trials = await evaluator.test(task_with_answer=task_with_answer, num_trials=num_trials,
        task_assignment_callback=task_assignment_callback, use_memory=True, reset_memory=True, client=client,
        page_log=page_log, memory_dir=memory_dir)
    success_rate = round((num_successes / num_trials) * 100)
    page.add_lines("\nSuccess rate:  {}%\n".format(success_rate), flush=True)

    # Provide the demonstration.
    page.add_lines("Demonstrate a solution to a similar task.")
    demo_task = "You are a telecommunications engineer who wants to build cell phone towers on a stretch of road. Houses are located at mile markers 17, 20, 19, 10, 11, 12, 3, 6. Each cell phone tower can cover houses located next to the road within a 4-mile radius. Find the minimum number of cell phone towers needed to cover all houses next to the road. Your answer should be a positive numerical integer value."
    demonstration = "Sort the houses by location:  3, 6, 10, 11, 12, 17, 19, 20. Then start at one end and place the towers only where absolutely needed. The house at 3 could be served by a tower as far away as mile marker 7, because 3 + 4 = 7, so place a tower at 7. This obviously covers houses up to mile 7. But a coverage radius of 4 miles (in each direction) means a total coverage of 8 miles. So the tower at mile 7 would reach all the way to mile 11, covering the houses at 10 and 11. The next uncovered house would be at mile 12 (not 10), requiring a second tower. It could go at mile 16 (which is 12 + 4) and this tower would reach up to mile 20 (16 + 4), covering the remaining houses. So 2 towers would be enough."
    memory = AgenticMemoryController(reset=False, client=client, page_log=page_log, memory_dir=memory_dir)
    await memory.learn_from_demonstration(demo_task, demonstration)

    # Now test again to see if the demonstration (retrieved from memory) helps.
    page.add_lines("Assign the task again to see if the demonstration helps.")
    num_successes, num_trials = await evaluator.test(task_with_answer=task_with_answer, num_trials=num_trials,
        task_assignment_callback=task_assignment_callback, use_memory=True, reset_memory=False, client=client,
        page_log=page_log, memory_dir=memory_dir)
    success_rate = round((num_successes / num_trials) * 100)
    page.add_lines("\nSuccess rate:  {}%\n".format(success_rate), flush=True)

    page_log.finish_page(page)


async def eval_self_teaching(apprentice, evaluator, task_assignment_callback, client, page_log, memory_dir, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_self_teaching",
        details='',
        method_call="eval_self_teaching")

    # Choose the tasks from those listed at the top.
    task_index_list = [3, 1]

    # Train and test on any number of tasks using memory.
    tasklist = define_tasks_with_answers()
    task_with_answer_list = [tasklist[task_index] for task_index in task_index_list]

    total_num_successes_list = [0 for _ in task_index_list]
    total_num_trials = 0
    for i in range(settings["num_loops"]):
        # Always train on the first task.
        memory = AgenticMemoryController(reset=True, client=client, page_log=page_log, memory_dir=memory_dir)
        task_with_answer = task_with_answer_list[0]
        await memory.train_on_task(
            task=task_with_answer["task"],
            expected_answer=task_with_answer["expected_answer"],
            task_assignment_callback=task_assignment_callback,
            final_format_instructions="",
            max_train_trials=settings["max_train_trials"],
            max_test_trials=settings["max_test_trials"])

        # Test on all tasks.
        for j, task_with_answer in enumerate(task_with_answer_list):
            num_successes, num_trials = await evaluator.test(
                task_with_answer=task_with_answer,
                num_trials=settings["num_final_test_trials"],
                task_assignment_callback=task_assignment_callback,
                use_memory=True,
                reset_memory=False,
                client=client,
                page_log=page_log,
                memory_dir=memory_dir)
            page.add_lines("Success rate ({}):  {}%".format(j, round((num_successes / num_trials) * 100)), flush=True)
            print("SUCCESS RATE ({}):  {}%\n".format(j, round((num_successes / num_trials) * 100)))
            total_num_successes_list[j] += num_successes
        total_num_trials += settings["num_final_test_trials"]
        page.add_lines("")

    for i, total_num_successes in enumerate(total_num_successes_list):
        success_rate = round((total_num_successes / total_num_trials) * 100)
        page.add_lines("\nOverall success rate ({}):  {}%\n".format(i, success_rate), flush=True)

    page_log.finish_page(page)


class Evaluator:
    def __init__(self):
        self.page_log = None

    def create_client(self, settings):
        client = None
        provider = settings["provider"]
        if provider == "openai":
            client = self.create_oai_client(settings)
        elif provider == "azure_openai":
            client = self.create_aoai_client(settings)
        elif provider == "trapi":
            client = self.create_trapi_client(settings)
        else:
            assert False, "Invalid client provider"

        # Check if the client should be wrapped.
        if "wrapper" in settings:
            wrapper_settings = settings["wrapper"]
            if wrapper_settings["enabled"]:
                # Wrap the client.
                client = ClientWrapper(
                    client, wrapper_settings["mode"], wrapper_settings["session_name"], self.page_log)

        return client

    def create_oai_client(self, settings):
        # Create an OpenAI client
        model_name = "gpt-4o-2024-08-06"
        client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=settings["api_key"],
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            presence_penalty=settings["presence_penalty"],
            frequency_penalty=settings["frequency_penalty"],
            top_p=settings["top_p"],
            max_retries=settings["max_retries"],
        )
        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through OpenAI directly")
        self.page_log.append_entry_line("  temperature:  {}".format(settings["temperature"]))
        return client

    def create_aoai_client(self, settings):
        # Create an Azure OpenAI client
        token_provider = get_bearer_token_provider(DefaultAzureCredential(),
                                                   "https://cognitiveservices.azure.com/.default")
        azure_deployment = "gpt-4o-2024-08-06-eval"
        model = "gpt-4o-2024-08-06"
        azure_endpoint = "https://agentic2.openai.azure.com/"
        client = AzureOpenAIChatCompletionClient(
            azure_endpoint=azure_endpoint,
            azure_ad_token_provider=token_provider,
            azure_deployment=azure_deployment,
            api_version="2024-06-01",
            model=model,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            presence_penalty=settings["presence_penalty"],
            frequency_penalty=settings["frequency_penalty"],
            top_p=settings["top_p"],
            max_retries=settings["max_retries"],
        )
        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through Azure OpenAI")
        self.page_log.append_entry_line("  temperature:  {}".format(settings["temperature"]))
        return client

    def create_trapi_client(self, settings):
        # Create an Azure OpenAI client through TRAPI
        token_provider = get_bearer_token_provider(ChainedTokenCredential(
            AzureCliCredential(),
            DefaultAzureCredential(
                exclude_cli_credential=True,
                # Exclude other credentials we are not interested in.
                exclude_environment_credential=True,
                exclude_shared_token_cache_credential=True,
                exclude_developer_cli_credential=True,
                exclude_powershell_credential=True,
                exclude_interactive_browser_credential=True,
                exclude_visual_studio_code_credentials=True,
                # managed_identity_client_id=os.environ.get("DEFAULT_IDENTITY_CLIENT_ID"),  # See the TRAPI docs
            )
        ), "api://trapi/.default")
        model = "gpt-4o-2024-08-06"  # This is (for instance) the OpenAI model name, which is used to look up capabilities.
        azure_deployment = 'gpt-4o_2024-08-06'  # This is DeploymentName in the table at https://aka.ms/trapi/models
        trapi_suffix = 'msraif/shared'  # This is TRAPISuffix (without /openai) in the table at https://aka.ms/trapi/models
        endpoint = f'https://trapi.research.microsoft.com/{trapi_suffix}'
        api_version = '2024-10-21'  # From https://learn.microsoft.com/en-us/azure/ai-services/openai/api-version-deprecation#latest-ga-api-release
        client = AzureOpenAIChatCompletionClient(
            azure_ad_token_provider=token_provider,
            model=model,
            azure_deployment=azure_deployment,
            azure_endpoint=endpoint,
            api_version=api_version,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            presence_penalty=settings["presence_penalty"],
            frequency_penalty=settings["frequency_penalty"],
            top_p=settings["top_p"],
            max_retries=settings["max_retries"],
        )
        self.page_log.append_entry_line("Client:  {}".format(client._resolved_model))
        self.page_log.append_entry_line("  created through TRAPI")
        self.page_log.append_entry_line("  temperature:  {}".format(settings["temperature"]))
        return client

    async def assign_task_to_magentic_one(self, task, model_client, page_log) -> Tuple[str, str]:
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

        # Get the team's text response to the task.
        stream = team.run_stream(task=task)
        task_result = await Console(stream)
        response_str = "\n".join([message_content_to_str(message.content) for message in task_result.messages])
        page.add_lines("\n-----  RESPONSE  -----\n\n{}\n".format(response_str), flush=True)

        # MagenticOne's response is the chat history, which we use here as the work history.
        work_history = response_str

        page_log.finish_page(page)
        return response_str, work_history

    async def assign_task_to_client(self, task, client, page_log):
        page = page_log.begin_page(
            summary="assign_task_to_client",
            details='',
            method_call="assign_task_to_client")

        page.add_lines(task)

        system_message_content = """You are a helpful and thoughtful assistant.
In responding to every user message, you follow the same multi-step process given here:
1. Explain your understanding of the user message in detail, covering all the important points.
2. List as many possible responses as you can think of.
3. Carefully list and weigh the pros and cons (if any) of each possible response.
4. Critique the pros and cons above, looking for any flaws in your reasoning. But don't make up flaws that don't exist.
5. Decide on the best response, looping back to step 1 if none of the responses are satisfactory.
6. Finish by providing your final response in the particular format requested by the user."""

        system_message = SystemMessage(content=system_message_content)
        user_message = UserMessage(content=task, source="User")

        input_messages = [system_message] + [user_message]
        response = await client.create(input_messages)
        response_str = response.content

        # Log the model call
        page_log.add_model_call(description="Ask the model",
                                details="to complete the task", input_messages=input_messages,
                                response=response,
                                num_input_tokens=0, caller='assign_task_to_client')
        page.add_lines("\n-----  RESPONSE  -----\n\n{}\n".format(response_str), flush=True)

        # Use the response as the work history as well.
        work_history = response_str

        page_log.finish_page(page)
        return response_str, work_history

    async def test(self, task_with_answer, num_trials, task_assignment_callback, use_memory, reset_memory,
                   client, page_log, memory_dir) -> Tuple[str, int, int]:
        page = page_log.begin_page(
            summary="Evaluator.test",
            details='',
            method_call="Evaluator.test")

        grader = Grader(client, page_log)

        if use_memory:
            page.add_lines("Testing with memory.\n", flush=True)
            memory = AgenticMemoryController(reset=reset_memory, client=client, page_log=page_log,
                                             memory_dir=memory_dir)
            response, num_successes, num_trials = await memory.test_on_task(
                task=task_with_answer["task"],
                expected_answer=task_with_answer["expected_answer"],
                task_assignment_callback=task_assignment_callback,
                num_trials=num_trials)
        else:
            page.add_lines("Testing without memory.\n", flush=True)
            response = None
            num_successes = 0
            for trial in range(num_trials):
                page.add_lines("\n-----  TRIAL {}  -----\n".format(trial + 1), flush=True)
                page.add_lines("Try to solve the task.\n", flush=True)
                response, _ = await task_assignment_callback(task_with_answer["task"], client, page_log)

                response_is_correct, extracted_answer = await grader.is_response_correct(
                    task_with_answer["task"], response, task_with_answer["expected_answer"])
                page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
                if response_is_correct:
                    page.add_lines("Answer is CORRECT.\n", flush=True)
                    num_successes += 1
                else:
                    page.add_lines("Answer is INCORRECT.\n", flush=True)

        page.add_lines("\nSuccess rate:  {}%\n".format(round((num_successes / num_trials) * 100)), flush=True)

        page_log.finish_page(page)
        return num_successes, num_trials

    async def run(self, settings_filepath):
        # Load the settings from yaml.
        with open(settings_filepath, "r") as file:
            settings = yaml.load(file, Loader=yaml.FullLoader)
            evaluator_settings = settings["evaluator"]

            # Create the PageLog.
            self.page_log = PageLog(evaluator_settings["pagelog"])
            page = self.page_log.begin_page(
                summary="main",
                details='',
                method_call="main")

            # Create the client, which is used by both the apprentice and the evaluator.
            client = self.create_client(settings["client"])

            # Create the apprentice.
            apprentice_settings = settings["apprentice"]
            apprentice = Apprentice(settings["apprentice"], self, client, self.page_log)

            # Configure the agentic memory controller.
            agentic_memory_controller_settings = apprentice_settings["agentic_memory_controller"]
            agentic_memory_bank_settings = agentic_memory_controller_settings["agentic_memory_bank"]

            # Configure the agent wrapper.
            agent_wrapper_settings = apprentice_settings["agent_wrapper"]

            # Configure the base agent.
            base_agent = agent_wrapper_settings["base_agent"]
            if base_agent == "magentic_one":
                task_assignment_callback = self.assign_task_to_magentic_one
            elif base_agent == "thin_agent":
                task_assignment_callback = self.assign_task_to_client
            else:
                assert False, "Invalid base agent"

            # Execute each evaluations.
            memory_path = agentic_memory_bank_settings["path"]
            for ev in settings["evaluations"]:
                eval_function = globals()[ev["name"]]
                await eval_function(apprentice, self, task_assignment_callback, client, self.page_log, memory_path, ev)

            if hasattr(client, "finalize"):
                # If this is a client wrapper, it needs to be finalized.
                client.finalize()

            self.page_log.flush(final=True)  # Finalize the page log
            self.page_log.finish_page(page)


class Apprentice:
    def __init__(self, settings, evaluator, client, page_log):
        self.settings = settings
        self.evaluator = evaluator
        self.client = client
        self.page_log = page_log
        self.memory_settings = settings["agentic_memory_controller"]
        self.agent_settings = settings["agent_wrapper"]
        self.memory = None
        self.agent = None

    def create_memory(self, reset_memory):
        self.memory = AgenticMemoryController(
            reset=reset_memory,
            client=self.client,
            page_log=self.page_log,
            memory_dir=self.memory_settings["agentic_memory_bank"]["path"]
        )

    def create_agent(self):
        return None

    def start(self, reset_memory):
        self.create_memory(reset_memory)
        self.create_agent()

    def stop(self):
        self.memory = None
        self.agent = None

    async def handle_user_message(self, text, task_assignment_callback, should_await=True):
        page = self.page_log.begin_page(
            summary="Apprentice.handle_user_message",
            details="",
            method_call="Apprentice.handle_user_message")

        # Pass the user message through to the memory controller.
        response = await self.memory.handle_user_message(text, task_assignment_callback, should_await)

        self.page_log.finish_page(page)
        return response


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Usage:  amt.py <path to *.yaml file>")
    else:
        evaluator = Evaluator()
        asyncio.run(evaluator.run(settings_filepath=args[0]))
