"""
To run, type 
`python packages/autogen-core/samples/common/adas/adas.py --data_filename=<path_to_data>`

"""

import argparse
import asyncio
import json
import logging
import os
import random
import time
import uuid
import numpy as np
from dataclasses import dataclass
from typing import Dict, List
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from autogen_core.components import RoutedAgent, default_subscription, message_handler
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import MessageContext
from autogen_core.components import DefaultTopicId
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

# TODO fix imports
import sys

sys.path.append("/home/andyye/autogen/python/packages/autogen-core/samples/")
from common.utils import get_chat_completion_client_from_envs

from adas_prompt import get_init_archive, get_prompt, get_reflexion_prompt
from utils import random_id, bootstrap_confidence_interval, load_drop, drop_metric


logging.basicConfig(level=logging.WARNING)
logging.getLogger("autogen_core").setLevel(logging.DEBUG)

Info = namedtuple("Info", ["name", "author", "content", "iteration_idx"])

SEARCHING_MODE = True


@dataclass
class ADASTask:
    task: str


@dataclass
class ADASResult:
    result: str


@dataclass
class LLMMessageList:
    llm_message_list: List[LLMMessage]


@dataclass
class SimpleReflectAgentResponse:
    json_content: Dict[str, str]
    # content: str


@dataclass
class LLMAgentBaseTask:
    system_message: LLMMessage
    instruction: LLMMessage
    input_infos: List[Info]
    iteration_idx: int
    output_fields: List[str]
    role: str


@dataclass
class Message:
    content: str


class AgentSystem:
    def __init__(self) -> None:
        pass


def generate_task(input_infos) -> str:

    # construct input infos text
    input_infos_text = ""
    for input_info in input_infos:
        if isinstance(input_info, Info):
            (field_name, author, content, iteration_idx) = input_info
        else:
            continue

        if field_name == "task":
            input_infos_text += f"# Your Task:\n{content}\n\n"
        elif iteration_idx != -1:
            # input_infos_text += f'### {field_name} #{iteration_idx + 1} by {author}:\n{content}\n\n'
            input_infos_text += f"### {field_name} #{iteration_idx + 1}:\n{content}\n\n"
        else:
            # input_infos_text += f'### {field_name} by {author}:\n{content}\n\n'
            input_infos_text += f"### {field_name}:\n{content}\n\n"

    prompt = input_infos_text + "# Instruction: \n"
    return prompt


def evaluate_forward_fn(args, forward_str):
    # dynamically define forward()
    # modified from https://github.com/luchris429/DiscoPOP/blob/main/scripts/launch_evo.py
    namespace = {}
    print(f"forward str {forward_str}")
    exec(forward_str, globals(), namespace)
    names = list(namespace.keys())
    if len(names) != 1:
        raise AssertionError(f"{len(names)} things in namespace. Please only provide 1")
    func = namespace[names[0]]
    if not callable(func):
        raise AssertionError(f"{func} is not callable")
    setattr(AgentSystem, "forward", func)

    # set seed 0 for valid set
    examples = load_drop(args.data_filename)[
        1:-1
    ]  # first one and the last one is for few-shot examples
    random.seed(args.shuffle_seed)
    random.shuffle(examples)

    if SEARCHING_MODE:
        examples = examples[: args.valid_size] * args.n_repeat
    else:
        examples = (
            examples[args.valid_size : args.valid_size + args.test_size] * args.n_repeat
        )

    questions = [example["inputs"] for example in examples]
    answers = [example["targets"] for example in examples]

    print(f"problem length: {len(examples)}")
    max_workers = min(len(examples), args.max_workers) if args.multiprocessing else 1

    task_queue = []
    for q in questions:
        taskInfo = Info("task", "User", q, -1)
        task_queue.append((taskInfo, AgentSystem()))

    # agentSystem = AgentSystem()

    def call_forward(agent_task_queue):
        taskInfo, agent = agent_task_queue
        print(f"taskInfo {taskInfo}")
        task = generate_task([taskInfo])

        # For magentic one using the create_completion_client_from_env() helper
        agent_model_kwargs = {}

        result = agent.forward(task, agent_model_kwargs)
        if args.thread_sleep:
            print(f"Sleeping for {args.thread_sleep}")
            time.sleep(args.thread_sleep)
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(
            tqdm(executor.map(call_forward, task_queue), total=len(task_queue))
        )

    acc_list = []
    for q_idx, res in enumerate(results):
        try:
            if isinstance(res, Info):
                extracted_answer = res.content
            else:
                extracted_answer = res
            correct_answers = answers[q_idx]
            print(
                f"extracted_answer {extracted_answer}, correct_answers {correct_answers}"
            )
            em_score, f1_score = drop_metric(extracted_answer, correct_answers)
        except Exception as e:
            acc_list.append(0)
            continue

        acc_list.append(f1_score)

    print(f"f1: {bootstrap_confidence_interval(acc_list)}")
    return acc_list


@default_subscription
class ADASAgent(RoutedAgent):
    """An agent that performs ADAS."""

    def __init__(
        self, model_client: ChatCompletionClient, system_prompt: str, args, archive
    ) -> None:
        super().__init__("An agent searching agent.")
        self._args = args
        self._archive = archive
        self._model_client = model_client
        self._session_memory: Dict[str, List[ADASTask | ADASResult]] = {}

        self._system_messages: List[LLMMessage] = [
            # SystemMessage is not allowed in o1-preview API.
            # SystemMessage(
            AssistantMessage(
                content=system_prompt,
                source=self.id.type,
            )
        ]
        self._chat_history: List[LLMMessage] = []
        self._model_client = model_client

    @message_handler
    async def handle_task(
        self, message: LLMMessageList, ctx: MessageContext
    ) -> SimpleReflectAgentResponse:
        print(f"Meta-Agent making a LLM call...")
        logging.info(f"{self._description} received message: {message}")
        model_result = await self._model_client.create(
            self._system_messages + message.llm_message_list
        )

        assert isinstance(model_result.content, str)
        print(f"Model client result: {model_result.content}")
        print("Loading the json string of the content...")
        json_content = json.loads(model_result.content)
        print("Finished loading the json string of the content")
        return SimpleReflectAgentResponse(json_content=json_content)

    @message_handler
    async def handle_adas_task(self, message: ADASTask, ctx: MessageContext) -> None:
        # Store the messages in a temporary memory for this request only.
        session_id = str(uuid.uuid4())
        self._session_memory.setdefault(session_id, []).append(message)

        # Process archive
        file_path = os.path.join(args.save_dir, f"{args.expr_name}_run_archive.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:
                archive = json.load(json_file)
            if "generation" in archive[-1] and isinstance(
                archive[-1]["generation"], int
            ):
                start = archive[-1]["generation"]
            else:
                start = 0
        else:
            archive = get_init_archive()
            start = 0

        for solution in archive:
            if "fitness" in solution:
                continue

            solution["generation"] = "initial"
            print(f"============Initial Archive: {solution['name']}=================")
            try:
                acc_list = evaluate_forward_fn(args, solution["code"])
            except Exception as e:
                print("During evaluating initial archive:")
                print(e)
                continue

            fitness_str = bootstrap_confidence_interval(acc_list)
            solution["fitness"] = fitness_str

            # save results
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as json_file:
                json.dump(archive, json_file, indent=4)

        # Initial prompt
        for n in range(start, args.n_generation):
            print(f"============Generation {n + 1}=================")

            # Set prompt with updated archive (for n > 0)
            _, prompt = get_prompt(archive)

            msg_list = [UserMessage(content=prompt, source=self.metadata["type"])]
            try:
                response = await self.send_message(LLMMessageList(msg_list), self.id)
                next_solution = response.json_content
                (
                    reflexion_prompt_1,
                    reflexion_prompt_2,
                    reflexion_prompt_3,
                    reflexion_prompt_4,
                ) = get_reflexion_prompt(self._archive[-1] if n > 0 else None)
                print(f"--After initial prompt {response}")

                # Reflexion 1
                new_messages = msg_list + [
                    AssistantMessage(
                        content=str(next_solution), source=self.metadata["type"]
                    ),
                    UserMessage(
                        content=reflexion_prompt_1, source=self.metadata["type"]
                    ),
                ]
                response = await self.send_message(
                    LLMMessageList(new_messages), self.id
                )
                next_solution = response.json_content
                print(f"--After reflexion_prompt_1 {response}")

                # Reflexion 2
                new_messages = new_messages + [
                    AssistantMessage(
                        content=str(next_solution), source=self.metadata["type"]
                    ),
                    UserMessage(
                        content=reflexion_prompt_2, source=self.metadata["type"]
                    ),
                ]
                response = await self.send_message(
                    LLMMessageList(new_messages), self.id
                )
                next_solution = response.json_content
                print(f"--After reflexion_prompt_2 {next_solution}")

                # Reflexion 3
                new_messages = new_messages + [
                    AssistantMessage(
                        content=str(next_solution), source=self.metadata["type"]
                    ),
                    UserMessage(
                        content=reflexion_prompt_3, source=self.metadata["type"]
                    ),
                ]
                response = await self.send_message(
                    LLMMessageList(new_messages), self.id
                )
                next_solution = response.json_content
                print(f"--After reflexion_prompt_3 {next_solution}")

                # Reflexion 4
                new_messages = new_messages + [
                    AssistantMessage(
                        content=str(next_solution), source=self.metadata["type"]
                    ),
                    UserMessage(
                        content=reflexion_prompt_4, source=self.metadata["type"]
                    ),
                ]
                response = await self.send_message(
                    LLMMessageList(new_messages), self.id
                )
                next_solution = response.json_content
                print(f"--After reflexion_prompt_4 {next_solution}")

                # next_solution = {'reflection': 'Upon reviewing the code and the official API documentation, I noticed that the "AzureOpenAIChatCompletionClient" requires the "azure_deployment" parameter, which was missing in the code. According to the documentation, we need to provide "azure_deployment" along with "model", "api_version", and "azure_endpoint". I have updated the code to include the "azure_deployment" parameter when creating the model client. Additionally, I ensured that all other parameters and imports align with the official API documentation.', 'thought': '**Insights:**\nDecomposing complex questions into simpler sub-questions can improve reasoning accuracy by allowing the model to focus on one aspect at a time.\n\n**Overall Idea:**\nImplement an agent system where a `DecomposerAgent` breaks down the main question into sub-questions. `SolverAgents` answer these sub-questions based on the provided passage, and a `ComposerAgent` combines the sub-answers to produce the final answer.\n\n**Implementation:**\n- Define a `DecomposerAgent` that decomposes the main question into sub-questions and distributes them.\n- Define `SolverAgents` that answer sub-questions based on the provided passage.\n- Define a `ComposerAgent` that collects sub-answers and composes the final answer.\n- Use appropriate message classes and ensure correct message passing and subscriptions.\n- The `ComposerAgent` publishes the final answer to the default topic, which is collected by a `ClosureAgent`.', 'name': 'Question Decomposition Agent', 'code': 'def forward(self, task, model_client_kwargs) -> str:\n    import asyncio\n    from dataclasses import dataclass\n    from typing import List\n    from azure.identity import DefaultAzureCredential, get_bearer_token_provider\n    from autogen_core.base import AgentId, AgentRuntime, MessageContext\n    from autogen_core.components import DefaultTopicId, default_subscription, RoutedAgent, message_handler, ClosureAgent\n    from autogen_core.components.models import AssistantMessage, UserMessage, SystemMessage, ChatCompletionClient\n    from autogen_ext.models import AzureOpenAIChatCompletionClient\n    from autogen_core.application import SingleThreadedAgentRuntime\n\n    # Create the Azure OpenAI model client\n    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")\n    model_client = AzureOpenAIChatCompletionClient(\n        azure_deployment=model_client_kwargs["azure_deployment"],\n        model=model_client_kwargs["model"],\n        api_version=model_client_kwargs["api_version"],\n        azure_endpoint=model_client_kwargs["azure_endpoint"],\n        azure_ad_token_provider=token_provider,\n        model_capabilities={\n            "vision": True,\n            "function_calling": True,\n            "json_output": True,\n        },\n    )\n\n    @dataclass\n    class Task:\n        content: str\n\n    @dataclass\n    class SubQuestion:\n        question: str\n        sub_question: str\n\n    @dataclass\n    class SubQuestionList:\n        sub_questions: List[str]\n\n    @dataclass\n    class SubAnswer:\n        sub_question: str\n        answer: str\n\n    @dataclass\n    class FinalAnswer:\n        answer: str\n\n    @default_subscription\n    class DecomposerAgent(RoutedAgent):\n        def __init__(self, model_client: ChatCompletionClient) -> None:\n            super().__init__("Decomposer Agent")\n            self._model_client = model_client\n            self._system_messages = [\n                SystemMessage(\n                    content=(\n                        "You are an expert at decomposing complex questions into simpler sub-questions that can be answered individually."\n                    )\n                )\n            ]\n\n        @message_handler\n        async def handle_task(self, message: Task, ctx: MessageContext) -> None:\n            user_message = UserMessage(\n                content=(\n                    f"Decompose the following question into a list of sub-questions that can help answer the main question:\\n{message.content}"\n                ),\n                source="user"\n            )\n            messages = self._system_messages + [user_message]\n            response = await self._model_client.create(messages=messages, cancellation_token=ctx.cancellation_token)\n            assert isinstance(response.content, str)\n            # Assuming the model lists the sub-questions in numbered format\n            sub_questions = [sq.strip() for sq in response.content.strip().split(\'\\n\') if sq.strip()]\n            for sq in sub_questions:\n                await self.publish_message(\n                    SubQuestion(question=message.content, sub_question=sq),\n                    topic_id=DefaultTopicId(),\n                )\n            # Send the list of sub-questions to the ComposerAgent\n            await self.publish_message(\n                SubQuestionList(sub_questions=sub_questions),\n                topic_id=DefaultTopicId(),\n            )\n\n    @default_subscription\n    class SolverAgent(RoutedAgent):\n        def __init__(self, model_client: ChatCompletionClient, passage: str) -> None:\n            super().__init__("Solver Agent")\n            self._model_client = model_client\n            self._system_messages = [\n                SystemMessage(\n                    content=(\n                        "You are a helpful assistant that answers questions based on the provided passage. "\n                        "Provide concise and accurate answers."\n                    )\n                )\n            ]\n            self._passage = passage\n\n        @message_handler\n        async def handle_sub_question(self, message: SubQuestion, ctx: MessageContext) -> None:\n            user_message = UserMessage(\n                content=(\n                    f"Passage:\\n{self._passage}\\n\\nQuestion:\\n{message.sub_question}\\n\\nAnswer the question based on the passage."\n                ),\n                source="user"\n            )\n            messages = self._system_messages + [user_message]\n            response = await self._model_client.create(messages=messages, cancellation_token=ctx.cancellation_token)\n            assert isinstance(response.content, str)\n            await self.publish_message(\n                SubAnswer(sub_question=message.sub_question, answer=response.content),\n                topic_id=DefaultTopicId(),\n            )\n\n    @default_subscription\n    class ComposerAgent(RoutedAgent):\n        def __init__(self, model_client: ChatCompletionClient) -> None:\n            super().__init__("Composer Agent")\n            self._model_client = model_client\n            self._system_messages = [\n                SystemMessage(\n                    content=(\n                        "You are a helpful assistant that composes a final answer based on answers to sub-questions."\n                    )\n                )\n            ]\n            self._num_sub_questions = 0\n            self._sub_answers = []\n\n        @message_handler\n        async def handle_sub_question_list(self, message: SubQuestionList, ctx: MessageContext) -> None:\n            self._num_sub_questions = len(message.sub_questions)\n\n        @message_handler\n        async def handle_sub_answer(self, message: SubAnswer, ctx: MessageContext) -> None:\n            self._sub_answers.append(message)\n            if len(self._sub_answers) == self._num_sub_questions:\n                # All sub-answers have been collected\n                # Compose the final answer\n                sub_answers_text = \'\\n\'.join(\n                    f"Sub-question: {sa.sub_question}\\nAnswer: {sa.answer}" for sa in self._sub_answers\n                )\n                user_message = UserMessage(\n                content=(\n                    f"Based on the following sub-questions and their answers, compose a final comprehensive answer to the main question.\\n{sub_answers_text}"\n                    ),\n                    source="user"\n                )\n                messages = self._system_messages + [user_message]\n                response = await self._model_client.create(messages=messages, cancellation_token=ctx.cancellation_token)\n                assert isinstance(response.content, str)\n                await self.publish_message(\n                    FinalAnswer(answer=response.content),\n                    topic_id=DefaultTopicId(),\n                )\n\n    async def main():\n        queue = asyncio.Queue()\n        async def output_result(_runtime: AgentRuntime, id: AgentId, message: FinalAnswer, ctx: MessageContext) -> None:\n            await queue.put(message)\n\n        runtime = SingleThreadedAgentRuntime()\n\n        # Register agents\n        await DecomposerAgent.register(runtime, "decomposer_agent", lambda: DecomposerAgent(model_client))\n        await SolverAgent.register(runtime, "solver_agent", lambda: SolverAgent(model_client, passage=task))\n        await ComposerAgent.register(runtime, "composer_agent", lambda: ComposerAgent(model_client))\n\n        # ClosureAgent to collect the final answer\n        await ClosureAgent.register(runtime, "output_result", output_result)\n\n        runtime.start()\n\n        # Publish the task to the DecomposerAgent\n        await runtime.publish_message(\n            Task(content=task),\n            topic_id=DefaultTopicId(),\n        )\n\n        # Keep processing messages until idle.\n        await runtime.stop_when_idle()\n\n        # Return the answer from the queue\n        final_answer = (await queue.get()).answer\n        return final_answer\n\n    return asyncio.run(main())'}
                # next_solution = {'reflection': 'Upon reviewing the code and the official API documentation, I noticed that the "AzureOpenAIChatCompletionClient" requires the "azure_deployment" parameter, which was missing in the code. According to the documentation, we need to provide "azure_deployment" along with "model", "api_version", and "azure_endpoint". I have updated the code to include the "azure_deployment" parameter when creating the model client. Additionally, I ensured that all other parameters and imports align with the official API documentation.', 'thought': '**Insights:**\nDecomposing complex questions into simpler sub-questions can improve reasoning accuracy by allowing the model to focus on one aspect at a time.\n\n**Overall Idea:**\nImplement an agent system where a `DecomposerAgent` breaks down the main question into sub-questions. `SolverAgents` answer these sub-questions based on the provided passage, and a `ComposerAgent` combines the sub-answers to produce the final answer.\n\n**Implementation:**\n- Define a `DecomposerAgent` that decomposes the main question into sub-questions and distributes them.\n- Define `SolverAgents` that answer sub-questions based on the provided passage.\n- Define a `ComposerAgent` that collects sub-answers and composes the final answer.\n- Use appropriate message classes and ensure correct message passing and subscriptions.\n- The `ComposerAgent` publishes the final answer to the default topic, which is collected by a `ClosureAgent`.', 'name': 'Question Decomposition Agent', 'code': 'def forward(self, task, model_client_kwargs) -> str:\n    import asyncio\n    from dataclasses import dataclass\n    from typing import List\n    from azure.identity import DefaultAzureCredential, get_bearer_token_provider\n    from autogen_core.base import AgentId, AgentRuntime, MessageContext\n    from autogen_core.components import DefaultTopicId, default_subscription, RoutedAgent, message_handler, ClosureAgent\n    from autogen_core.components.models import AssistantMessage, UserMessage, SystemMessage, ChatCompletionClient\n    from autogen_ext.models import AzureOpenAIChatCompletionClient\n    from autogen_core.application import SingleThreadedAgentRuntime\n\n    # Create the Azure OpenAI model client\n    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")\n    model_client = AzureOpenAIChatCompletionClient(\n        model=model_client_kwargs["model"],\n        api_version=model_client_kwargs["api_version"],\n        azure_endpoint=model_client_kwargs["azure_endpoint"],\n        azure_ad_token_provider=token_provider,\n        model_capabilities={\n            "vision": True,\n            "function_calling": True,\n            "json_output": True,\n        },\n    )\n\n    @dataclass\n    class Task:\n        content: str\n\n    @dataclass\n    class SubQuestion:\n        question: str\n        sub_question: str\n\n    @dataclass\n    class SubQuestionList:\n        sub_questions: List[str]\n\n    @dataclass\n    class SubAnswer:\n        sub_question: str\n        answer: str\n\n    @dataclass\n    class FinalAnswer:\n        answer: str\n\n    @default_subscription\n    class DecomposerAgent(RoutedAgent):\n        def __init__(self, model_client: ChatCompletionClient) -> None:\n            super().__init__("Decomposer Agent")\n            self._model_client = model_client\n            self._system_messages = [\n                SystemMessage(\n                    content=(\n                        "You are an expert at decomposing complex questions into simpler sub-questions that can be answered individually."\n                    )\n                )\n            ]\n\n        @message_handler\n        async def handle_task(self, message: Task, ctx: MessageContext) -> None:\n            user_message = UserMessage(\n                content=(\n                    f"Decompose the following question into a list of sub-questions that can help answer the main question:\\n{message.content}"\n                ),\n                source="user"\n            )\n            messages = self._system_messages + [user_message]\n            response = await self._model_client.create(messages=messages, cancellation_token=ctx.cancellation_token)\n            assert isinstance(response.content, str)\n            # Assuming the model lists the sub-questions in numbered format\n            sub_questions = [sq.strip() for sq in response.content.strip().split(\'\\n\') if sq.strip()]\n            for sq in sub_questions:\n                await self.publish_message(\n                    SubQuestion(question=message.content, sub_question=sq),\n                    topic_id=DefaultTopicId(),\n                )\n            # Send the list of sub-questions to the ComposerAgent\n            await self.publish_message(\n                SubQuestionList(sub_questions=sub_questions),\n                topic_id=DefaultTopicId(),\n            )\n\n    @default_subscription\n    class SolverAgent(RoutedAgent):\n        def __init__(self, model_client: ChatCompletionClient, passage: str) -> None:\n            super().__init__("Solver Agent")\n            self._model_client = model_client\n            self._system_messages = [\n                SystemMessage(\n                    content=(\n                        "You are a helpful assistant that answers questions based on the provided passage. "\n                        "Provide concise and accurate answers."\n                    )\n                )\n            ]\n            self._passage = passage\n\n        @message_handler\n        async def handle_sub_question(self, message: SubQuestion, ctx: MessageContext) -> None:\n            user_message = UserMessage(\n                content=(\n                    f"Passage:\\n{self._passage}\\n\\nQuestion:\\n{message.sub_question}\\n\\nAnswer the question based on the passage."\n                ),\n                source="user"\n            )\n            messages = self._system_messages + [user_message]\n            response = await self._model_client.create(messages=messages, cancellation_token=ctx.cancellation_token)\n            assert isinstance(response.content, str)\n            await self.publish_message(\n                SubAnswer(sub_question=message.sub_question, answer=response.content),\n                topic_id=DefaultTopicId(),\n            )\n\n    @default_subscription\n    class ComposerAgent(RoutedAgent):\n        def __init__(self, model_client: ChatCompletionClient) -> None:\n            super().__init__("Composer Agent")\n            self._model_client = model_client\n            self._system_messages = [\n                SystemMessage(\n                    content=(\n                        "You are a helpful assistant that composes a final answer based on answers to sub-questions."\n                    )\n                )\n            ]\n            self._num_sub_questions = 0\n            self._sub_answers = []\n\n        @message_handler\n        async def handle_sub_question_list(self, message: SubQuestionList, ctx: MessageContext) -> None:\n            self._num_sub_questions = len(message.sub_questions)\n\n        @message_handler\n        async def handle_sub_answer(self, message: SubAnswer, ctx: MessageContext) -> None:\n            self._sub_answers.append(message)\n            if len(self._sub_answers) == self._num_sub_questions:\n                # All sub-answers have been collected\n                # Compose the final answer\n                sub_answers_text = \'\\n\'.join(\n                    f"Sub-question: {sa.sub_question}\\nAnswer: {sa.answer}" for sa in self._sub_answers\n                )\n                user_message = UserMessage(\n                content=(\n                    f"Based on the following sub-questions and their answers, compose a final comprehensive answer to the main question.\\n{sub_answers_text}"\n                    ),\n                    source="user"\n                )\n                messages = self._system_messages + [user_message]\n                response = await self._model_client.create(messages=messages, cancellation_token=ctx.cancellation_token)\n                assert isinstance(response.content, str)\n                await self.publish_message(\n                    FinalAnswer(answer=response.content),\n                    topic_id=DefaultTopicId(),\n                )\n\n    async def main():\n        queue = asyncio.Queue()\n        async def output_result(_runtime: AgentRuntime, id: AgentId, message: FinalAnswer, ctx: MessageContext) -> None:\n            await queue.put(message)\n\n        runtime = SingleThreadedAgentRuntime()\n\n        # Register agents\n        await DecomposerAgent.register(runtime, "decomposer_agent", lambda: DecomposerAgent(model_client))\n        await SolverAgent.register(runtime, "solver_agent", lambda: SolverAgent(model_client, passage=task))\n        await ComposerAgent.register(runtime, "composer_agent", lambda: ComposerAgent(model_client))\n\n        # ClosureAgent to collect the final answer\n        await ClosureAgent.register(runtime, "output_result", output_result)\n\n        runtime.start()\n\n        # Publish the task to the DecomposerAgent\n        await runtime.publish_message(\n            Task(content=task),\n            topic_id=DefaultTopicId(),\n        )\n\n        # Keep processing messages until idle.\n        await runtime.stop_when_idle()\n\n        # Return the answer from the queue\n        final_answer = (await queue.get()).answer\n        return final_answer\n\n    return asyncio.run(main())'}

                # next_solution = {'reflection': '**Reflection:**\n\nAfter reviewing the "## WRONG Implementation examples" section, specifically example 8, I realized that for the `ClosureAgent` to receive the final `Answer` message correctly, the topic source in `publish_message` must match the agent key of the `ClosureAgent`. In the previous code, the `ReasoningAgent` published to `TopicId("result", self.id.type)` where `self.id.type` is `"reasoning_agent"`, but the `ClosureAgent` was registered with the agent key `"output_result"`. This mismatch would prevent the message from being delivered to the `ClosureAgent`.\n\nTo fix this, I adjusted the `ReasoningAgent` to publish the final `Answer` to `TopicId("result", "output_result")`, ensuring that the topic source matches the agent key of the `ClosureAgent`, which is `"output_result"`. This follows the correct pattern outlined in the examples and ensures that the message is correctly routed to the `ClosureAgent`.\n', 'thought': '**Insights:**\nBy parallelizing the generation of multiple reasoning paths, we can improve the efficiency of the agent. Additionally, ensuring that the agents and subscriptions are correctly set up will avoid common mistakes.\n\n**Overall Idea:**\nThe improved agent will generate multiple reasoning paths concurrently and aggregate the final answers to select the most common one. This enhances efficiency without altering the overall design.\n\n**Implementation:**\n- Use `asyncio.gather` to run multiple model calls concurrently in the `ReasoningAgent`.\n- Ensure that the agents and subscriptions are correctly registered.\n- Confirm that the `ClosureAgent` collects the final answer accurately.', 'name': 'Self-Consistency Chain-of-Thought Agent', 'code': 'def forward(self, task, model_client_kwargs):\n    import asyncio\n    import json\n    import logging\n    from collections import Counter\n    from dataclasses import dataclass\n    from typing import List\n    from autogen_core.base import MessageContext, AgentId, AgentRuntime, TopicId\n    from autogen_core.components import RoutedAgent, default_subscription, message_handler, ClosureAgent, TypeSubscription, DefaultTopicId\n    from autogen_core.components.models import (\n        AssistantMessage,\n        ChatCompletionClient,\n        LLMMessage,\n        SystemMessage,\n        UserMessage,\n    )\n    from autogen_core.application import SingleThreadedAgentRuntime\n    from autogen_ext.models import AzureOpenAIChatCompletionClient\n    from azure.identity import DefaultAzureCredential, get_bearer_token_provider\n\n    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")\n\n    # Create an AzureOpenAI model client.\n    model_client = AzureOpenAIChatCompletionClient(\n        model=model_client_kwargs["model"],\n        api_version=model_client_kwargs["api_version"],\n        azure_endpoint=model_client_kwargs["azure_endpoint"],\n        azure_ad_token_provider=token_provider,\n        model_capabilities={\n            "vision": True,\n            "function_calling": True,\n            "json_output": True\n        },\n    )\n\n    @dataclass\n    class Question:\n        content: str\n\n    @dataclass\n    class Answer:\n        content: str\n\n    @default_subscription\n    class ReasoningAgent(RoutedAgent):\n        def __init__(self, model_client: ChatCompletionClient, num_samples: int) -> None:\n            super().__init__("Reasoning Agent")\n            self._model_client = model_client\n            self._num_samples = num_samples\n\n        @message_handler\n        async def handle_question(self, message: Question, ctx: MessageContext) -> None:\n            async def generate_answer() -> str:\n                prompt = ("Please solve the following problem step-by-step:\\n\\n"\n                          f"{message.content}\\n\\n"\n                          "Your final answer should be a single string.")\n                messages = [\n                    SystemMessage("You are a helpful assistant for solving reasoning problems."),\n                    UserMessage(content=prompt, source="user"),\n                ]\n                response = await self._model_client.create(messages, cancellation_token=ctx.cancellation_token)\n                assert isinstance(response.content, str)\n                return response.content.strip()\n\n            # Generate the reasoning paths concurrently\n            tasks = [generate_answer() for _ in range(self._num_samples)]\n            final_answers = await asyncio.gather(*tasks)\n\n            # Aggregate the final answers and select the most common one\n            most_common_answer = Counter(final_answers).most_common(1)[0][0]\n\n            # Publish the final answer, ensuring topic source matches ClosureAgent\'s agent key\n            await self.publish_message(Answer(content=most_common_answer), topic_id=TopicId("result", "output_result"))\n\n    async def main():\n        queue = asyncio.Queue()\n\n        async def output_result(_runtime: AgentRuntime, id: AgentId, message: Answer, ctx: MessageContext) -> None:\n            await queue.put(message)\n\n        runtime = SingleThreadedAgentRuntime()\n\n        await ReasoningAgent.register(runtime, "reasoning_agent", lambda: ReasoningAgent(model_client, num_samples=5))\n\n        result_topic = TypeSubscription(topic_type="result", agent_type="output_result")\n        await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [result_topic])\n\n        runtime.start()\n        await runtime.publish_message(Question(content=task), DefaultTopicId())\n\n        await runtime.stop_when_idle()\n\n        return (await queue.get()).content\n\n    return asyncio.run(main())'}
                # next_solution = {'reflection': '**Reflection:**\n\nAfter reviewing the "## WRONG Implementation examples" section, specifically example 8, I realized that for the `ClosureAgent` to receive the final `Answer` message correctly, the topic source in `publish_message` must match the agent key of the `ClosureAgent`. In the previous code, the `ReasoningAgent` published to `TopicId("result", self.id.type)` where `self.id.type` is `"reasoning_agent"`, but the `ClosureAgent` was registered with the agent key `"output_result"`. This mismatch would prevent the message from being delivered to the `ClosureAgent`.\n\nTo fix this, I adjusted the `ReasoningAgent` to publish the final `Answer` to `TopicId("result", "output_result")`, ensuring that the topic source matches the agent key of the `ClosureAgent`, which is `"output_result"`. This follows the correct pattern outlined in the examples and ensures that the message is correctly routed to the `ClosureAgent`.\n', 'thought': '**Insights:**\nBy parallelizing the generation of multiple reasoning paths, we can improve the efficiency of the agent. Additionally, ensuring that the agents and subscriptions are correctly set up will avoid common mistakes.\n\n**Overall Idea:**\nThe improved agent will generate multiple reasoning paths concurrently and aggregate the final answers to select the most common one. This enhances efficiency without altering the overall design.\n\n**Implementation:**\n- Use `asyncio.gather` to run multiple model calls concurrently in the `ReasoningAgent`.\n- Ensure that the agents and subscriptions are correctly registered.\n- Confirm that the `ClosureAgent` collects the final answer accurately.', 'name': 'Self-Consistency Chain-of-Thought Agent', 'code': 'def forward(self, task, model_client_kwargs):\n    import asyncio\n    import json\n    import logging\n    from collections import Counter\n    from dataclasses import dataclass\n    from typing import List\n    from autogen_core.base import MessageContext, AgentId, AgentRuntime, TopicId\n    from autogen_core.components import RoutedAgent, default_subscription, message_handler, ClosureAgent, TypeSubscription, DefaultTopicId\n    from autogen_core.components.models import (\n        AssistantMessage,\n        ChatCompletionClient,\n        LLMMessage,\n        SystemMessage,\n        UserMessage,\n    )\n    from autogen_core.application import SingleThreadedAgentRuntime\n    from autogen_ext.models import AzureOpenAIChatCompletionClient\n    from azure.identity import DefaultAzureCredential, get_bearer_token_provider\n\n    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")\n\n    # Create an AzureOpenAI model client.\n    model_client = AzureOpenAIChatCompletionClient(\n        model=model_client_kwargs["model"],\n        api_version=model_client_kwargs["api_version"],\n        azure_endpoint=model_client_kwargs["azure_endpoint"],\n        azure_ad_token_provider=token_provider,\n        model_capabilities={\n            "vision": True,\n            "function_calling": True,\n            "json_output": True\n        },\n    )\n\n    @dataclass\n    class Question:\n        content: str\n\n    @dataclass\n    class Answer:\n        content: str\n\n    @default_subscription\n    class ReasoningAgent(RoutedAgent):\n        def __init__(self, model_client: ChatCompletionClient, num_samples: int) -> None:\n            super().__init__("Reasoning Agent")\n            self._model_client = model_client\n            self._num_samples = num_samples\n\n        @message_handler\n        async def handle_question(self, message: Question, ctx: MessageContext) -> None:\n            async def generate_answer() -> str:\n                prompt = ("Please solve the following problem step-by-step:\\n\\n"\n                          f"{message.content}\\n\\n"\n                          "Your final answer should be a single string.")\n                messages = [\n                    SystemMessage("You are a helpful assistant for solving reasoning problems."),\n                    UserMessage(content=prompt, source="user"),\n                ]\n                response = await self._model_client.create(messages, cancellation_token=ctx.cancellation_token)\n                assert isinstance(response.content, str)\n                return response.content.strip()\n\n            # Generate the reasoning paths concurrently\n            tasks = [generate_answer() for _ in range(self._num_samples)]\n            final_answers = await asyncio.gather(*tasks)\n\n            # Aggregate the final answers and select the most common one\n            most_common_answer = Counter(final_answers).most_common(1)[0][0]\n\n            # Publish the final answer, ensuring topic source matches ClosureAgent\'s agent key\n            await self.publish_message(Answer(content=most_common_answer), topic_id=TopicId("result", "output_result"))\n\n    async def main():\n        queue = asyncio.Queue()\n\n        async def output_result(_runtime: AgentRuntime, id: AgentId, message: Answer, ctx: MessageContext) -> None:\n            await queue.put(message)\n\n        runtime = SingleThreadedAgentRuntime()\n\n        await ReasoningAgent.register(runtime, "reasoning_agent", lambda: ReasoningAgent(model_client, num_samples=5))\n\n        result_topic = TypeSubscription(topic_type="result", agent_type="output_result")\n        await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [result_topic])\n\n        runtime.start()\n        await runtime.publish_message(Question(content=task), DefaultTopicId())\n\n        res = (await queue.get()).content\n\n        await runtime.stop()\n\n        return res\n\n    return asyncio.run(main())'}
            except Exception as e:
                print("Exception occured during the generation of new solution:")
                print(e)
                n -= 1
                continue

            acc_list = []
            for _ in range(args.debug_max):
                print("Evaluate code of newly generated solution. Debug loop...")
                try:
                    print(next_solution["code"])
                    acc_list = evaluate_forward_fn(args, next_solution["code"])
                    if np.mean(acc_list) < 0.01 and SEARCHING_MODE:
                        raise Exception("All 0 accuracy")
                    break
                except Exception as e:
                    print("During evaluation:")
                    print(e)
                    new_messages = new_messages + [
                        AssistantMessage(
                            content=str(next_solution), source=self.metadata["type"]
                        ),
                        UserMessage(
                            content=f"Error during evaluation:\n{e}\nCarefully consider where you went wrong in your latest implementation. Using insights from previous attempts, try to debug the current code to implement the same thought. Repeat your previous thought in 'thought', and put your thinking for debugging in 'debug_thought'",
                            source=self.metadata["type"],
                        ),
                    ]
                    try:
                        response = await self.send_message(
                            LLMMessageList(new_messages), self.id
                        )
                        next_solution = response.json_content
                    except Exception as e:
                        print("During LLM generate new solution:")
                        print(e)
                        continue
                    continue
            if not acc_list:
                n -= 1
                continue

            fitness_str = bootstrap_confidence_interval(acc_list)
            next_solution["fitness"] = fitness_str
            next_solution["generation"] = n + 1

            if "debug_thought" in next_solution:
                del next_solution["debug_thought"]
            if "reflection" in next_solution:
                del next_solution["reflection"]
            archive.append(next_solution)

            # save results
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as json_file:
                json.dump(archive, json_file, indent=4)


async def main(args) -> None:
    runtime = SingleThreadedAgentRuntime()
    client = get_chat_completion_client_from_envs(model="gpt-4o-mini")
    archive = get_init_archive()
    system_prompt, prompt = get_prompt(archive)

    await ADASAgent.register(
        runtime,
        "adas_agent",
        lambda: ADASAgent(
            model_client=client,
            system_prompt=system_prompt,
            args=args,
            archive=archive,
        ),
    )

    runtime.start()

    # Publish an initial message to trigger the ADAS search to start.
    await runtime.publish_message(
        message=ADASTask(task=prompt),
        topic_id=DefaultTopicId(),
    )

    # Keep processing messages until idle.
    await runtime.stop_when_idle()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ADAS")
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging."
    )
    parser.add_argument(
        "--data_filename", type=str, default="dataset/drop_v0_dev.jsonl.gz"
    )
    parser.add_argument("--valid_size", type=int, default=128)
    parser.add_argument("--test_size", type=int, default=800)
    parser.add_argument("--shuffle_seed", type=int, default=0)
    parser.add_argument("--n_repeat", type=int, default=1)
    parser.add_argument("--multiprocessing", action="store_true", default=True)
    parser.add_argument("--max_workers", type=int, default=48)
    parser.add_argument("--debug", action="store_true", default=True)
    parser.add_argument("--save_dir", type=str, default="results/")
    parser.add_argument("--expr_name", type=str, default="drop_gpt3.5_results")
    parser.add_argument("--n_generation", type=int, default=30)
    parser.add_argument("--debug_max", type=int, default=3)
    parser.add_argument(
        "--thread_sleep",
        type=int,
        default=0,
        help="Amount of time to sleep between new threads."
             "This is to mitigate any errors due to request limits with Azure or AutoGen",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-2024-05-13",
        choices=["gpt-4-turbo-2024-04-09", "gpt-3.5-turbo-0125", "gpt-4o-2024-05-13"],
    )
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("adas.log")
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(args))
