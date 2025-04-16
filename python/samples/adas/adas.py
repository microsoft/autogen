"""
ADAS implementation in AutoGen.

This script uses a meta-agent to search for novel agent
systems. Please read the README.md for more information.
"""

# pyright: basic
import asyncio
import importlib
import json
import logging
import os
import random
import time
import uuid
from argparse import ArgumentParser, Namespace
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Sequence, Union

import numpy as np
from adas_prompt import get_init_archive, get_prompt, get_reflexion_prompt
from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    default_subscription,
    message_handler,
)

# from autogen_core.base import MessageContext
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    # SystemMessage, # SystemMessage is not allowed in o1-preview API. TODO: Accomodate o1 model
    UserMessage,
)
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from pydantic import BaseModel
from tqdm import tqdm
from utils import bootstrap_confidence_interval

logging.basicConfig(level=logging.WARNING)
logging.getLogger("autogen_core").setLevel(logging.DEBUG)


@dataclass
class Info:
    def __init__(self, name: str, author: str, content: str, iteration_idx: int) -> None:
        self.name = name
        self.author = author
        self.content = content
        self.iteration_idx = iteration_idx


SEARCHING_MODE = True


@dataclass
class ADASTask:
    task: str


class LLMMessageList(BaseModel):
    llm_message_list: Sequence[LLMMessage]


@dataclass
class LLMResponse:
    json_content: Dict[str, str]


class AgentSystem:
    def __init__(self) -> None:
        pass


def generate_task(input_infos: List[Union[Info, Any]]) -> str:
    # construct input infos text
    input_infos_text = ""
    for input_info in input_infos:
        if isinstance(input_info, Info):
            (field_name, content, iteration_idx) = input_info.name, input_info.content, input_info.iteration_idx
        else:
            continue

        if field_name == "task":
            input_infos_text += f"# Your Task:\n{content}\n\n"
        elif iteration_idx != -1:
            input_infos_text += f"### {field_name} #{iteration_idx + 1}:\n{content}\n\n"
        else:
            input_infos_text += f"### {field_name}:\n{content}\n\n"

    prompt = input_infos_text + "# Instruction: \n"
    return prompt


def evaluate_forward_fn(arguments: Namespace, forward_str: str) -> List[float]:
    # Dynamically import benchmark-specific module given the path to the python file.
    # File must contain load_dataset and compute_metrics functions
    print(f"Loading functions from {arguments.benchmark_specific_utils_file}")
    spec = importlib.util.spec_from_file_location("module_name", arguments.benchmark_specific_utils_file)  # pyright: ignore reportAttributeAccessIssue
    module = importlib.util.module_from_spec(spec)  # pyright: ignore reportAttributeAccessIssue
    spec.loader.exec_module(module)

    # dynamically define forward()
    # modified from https://github.com/luchris429/DiscoPOP/blob/main/scripts/launch_evo.py
    namespace: Dict[str, Callable[[str, str], str]] = {}
    print(f"forward str {forward_str}")
    exec(forward_str, globals(), namespace)
    names: List[str] = list(namespace.keys())
    if len(names) != 1:
        raise AssertionError(f"{len(names)} things in namespace. Please only provide 1")
    func: Callable[[str, str], str] = namespace[names[0]]
    if not callable(func):
        raise AssertionError(f"{func} is not callable")
    AgentSystem.forward = func  # pyright: ignore reportAttributeAccessIssue

    # set seed 0 for valid set
    # first one and the last one is for few-shot examples
    examples: List[Dict[str, Any]] = list(module.load_dataset(arguments.data_filename)[1:-1])
    random.seed(arguments.shuffle_seed)
    random.shuffle(examples)

    if SEARCHING_MODE:
        examples = examples[: arguments.valid_size] * arguments.n_repeat
    else:
        examples = examples[arguments.valid_size : arguments.valid_size + arguments.test_size] * arguments.n_repeat

    questions: List[str] = [example["inputs"] for example in examples]
    answers: List[Any] = [example["targets"] for example in examples]

    print(f"problem length: {len(examples)}")
    max_workers = min(len(examples), arguments.max_workers) if arguments.multiprocessing else 1

    task_queue = []
    for q in questions:
        taskInfo = Info("task", "User", q, -1)
        task_queue.append((taskInfo, AgentSystem()))

    def call_forward(agent_task_queue: List[tuple[Info, AgentSystem]]) -> str:
        taskInfo, agent = agent_task_queue
        print(f"taskInfo {taskInfo}")
        task = generate_task([taskInfo])

        result: str = agent.forward(task, arguments.base_agent_model_config)  # pyright: ignore reportAttributeAccessIssue
        if arguments.thread_sleep:
            print(f"Sleeping for {arguments.thread_sleep}")
            time.sleep(arguments.thread_sleep)
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(executor.map(call_forward, task_queue), total=len(task_queue)))

    acc_list: List[float] = module.compute_metrics(results, answers)

    print(f"f1: {bootstrap_confidence_interval(acc_list)}")
    return acc_list


@default_subscription
class ADASAgent(RoutedAgent):
    """An agent that performs ADAS."""

    def __init__(
        self,
        model_client: ChatCompletionClient,
        system_prompt: str,
        args: Namespace,
        archive=None,
    ) -> None:
        super().__init__("An agent searching agent.")
        self._args = args
        self._archive = archive if archive else [{}]
        self._model_client = model_client
        self._session_memory: Dict[str, List[ADASTask]] = {}

        self._system_messages: Sequence[LLMMessage] = [
            # SystemMessage is not allowed in o1-preview API. TODO: Accomodate o1 model
            # SystemMessage(
            AssistantMessage(
                content=system_prompt,
                source=self.id.type,
            )
        ]
        self._chat_history: List[LLMMessage] = []
        self._model_client = model_client

    @message_handler
    async def handle_task(self, message: LLMMessageList, ctx: MessageContext) -> LLMResponse:
        print("Meta-Agent making a LLM call...")
        logging.info(f"{self._description} received message: {message}")
        model_result = await self._model_client.create(self._system_messages + message.llm_message_list)  # pyright: ignore reportAttributeAccessIssue

        assert isinstance(model_result.content, str)
        print(f"Model client result: {model_result.content}")
        print("Loading the json string of the content...")
        json_content = json.loads(model_result.content)
        print("Finished loading the json string of the content")
        return LLMResponse(json_content=json_content)

    @message_handler
    async def handle_adas_task(self, message: ADASTask, ctx: MessageContext) -> None:
        # Store the messages in a temporary memory for this request only.
        session_id = str(uuid.uuid4())
        self._session_memory.setdefault(session_id, []).append(message)

        # Process archive
        file_path = os.path.join(self._args.save_dir, f"{self._args.expr_name}_run_archive.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:  # noqa: ASYNC101
                archive = json.load(json_file)
            if "generation" in archive[-1] and isinstance(archive[-1]["generation"], int):
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
                acc_list = evaluate_forward_fn(self._args, solution["code"])
            except Exception as e:
                print("During evaluating initial archive:")
                print(e)
                continue

            fitness_str = bootstrap_confidence_interval(acc_list)
            solution["fitness"] = fitness_str

            # save results
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as json_file:  # noqa: ASYNC101
                json.dump(archive, json_file, indent=4)

        # Initial prompt
        for n in range(start, self._args.n_generation):
            print(f"============Generation {n + 1}=================")

            # Set prompt with updated archive (for n > 0)
            _, prompt = get_prompt(archive)

            msg_list = [UserMessage(content=prompt, source=self.metadata["type"])]
            try:
                response = await self.send_message(LLMMessageList(llm_message_list=msg_list), self.id)
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
                    AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    UserMessage(content=reflexion_prompt_1, source=self.metadata["type"]),
                ]
                response = await self.send_message(LLMMessageList(llm_message_list=new_messages), self.id)
                next_solution = response.json_content
                print(f"--After reflexion_prompt_1 {response}")

                # Reflexion 2
                new_messages = new_messages + [
                    AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    UserMessage(content=reflexion_prompt_2, source=self.metadata["type"]),
                ]
                response = await self.send_message(LLMMessageList(llm_message_list=new_messages), self.id)
                next_solution = response.json_content
                print(f"--After reflexion_prompt_2 {next_solution}")

                # Reflexion 3
                new_messages = new_messages + [
                    AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    UserMessage(content=reflexion_prompt_3, source=self.metadata["type"]),
                ]
                response = await self.send_message(LLMMessageList(llm_message_list=new_messages), self.id)
                next_solution = response.json_content
                print(f"--After reflexion_prompt_3 {next_solution}")

                # Reflexion 4
                new_messages = new_messages + [
                    AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    UserMessage(content=reflexion_prompt_4, source=self.metadata["type"]),
                ]
                response = await self.send_message(LLMMessageList(llm_message_list=new_messages), self.id)
                next_solution = response.json_content
                print(f"--After reflexion_prompt_4 {next_solution}")
            except Exception as e:
                print("Exception occured during the generation of new solution:")
                print(e)
                n -= 1
                continue

            acc_list = []
            for _ in range(self._args.debug_max):
                print("Evaluate code of newly generated solution. Debug loop...")
                try:
                    print(next_solution["code"])
                    acc_list = evaluate_forward_fn(self._args, next_solution["code"])
                    if np.mean(acc_list) < 0.01 and SEARCHING_MODE:
                        raise Exception("All 0 accuracy")
                    break
                except Exception as e:
                    print("During evaluation:")
                    print(e)
                    new_messages = new_messages + [
                        AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                        UserMessage(
                            content=f"Error during evaluation:\n{e}\nCarefully consider where you went wrong in your latest implementation. Using insights from previous attempts, try to debug the current code to implement the same thought. Repeat your previous thought in 'thought', and put your thinking for debugging in 'debug_thought'",
                            source=self.metadata["type"],
                        ),
                    ]
                    try:
                        response = await self.send_message(LLMMessageList(llm_message_list=new_messages), self.id)
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
            with open(file_path, "w") as json_file:  # noqa: ASYNC101
                json.dump(archive, json_file, indent=4)


async def main(arguments: Namespace) -> None:
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    # Create an AzureOpenAI model client.
    client = AzureOpenAIChatCompletionClient(
        azure_deployment=arguments.meta_agent_model_config["azure_deployment"],
        model=arguments.meta_agent_model_config["model"],
        api_version=arguments.meta_agent_model_config["api_version"],
        azure_endpoint=arguments.meta_agent_model_config["azure_endpoint"],
        azure_ad_token_provider=token_provider,
        model_capabilities=arguments.meta_agent_model_config["model_capabilities"],
    )

    runtime = SingleThreadedAgentRuntime()

    archive = get_init_archive()
    system_prompt, prompt = get_prompt(archive)

    await ADASAgent.register(
        runtime,
        "adas_agent",
        lambda: ADASAgent(
            model_client=client,
            system_prompt=system_prompt,
            args=arguments,
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
    parser = ArgumentParser(description="Run ADAS")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--data_filename", type=str, default="dataset/drop_v0_dev.jsonl.gz")
    parser.add_argument("--valid_size", type=int, default=128)
    parser.add_argument("--test_size", type=int, default=800)
    parser.add_argument("--shuffle_seed", type=int, default=0)
    parser.add_argument("--n_repeat", type=int, default=1)
    parser.add_argument("--multiprocessing", action="store_true", default=True)
    parser.add_argument("--max_workers", type=int, default=48)
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
        "--benchmark_specific_utils_file",
        type=str,
        default="utils_drop.py",
        help="File must contain load_dataset and compute_metrics functions.",
    )
    parser.add_argument(
        "--meta_agent_model_config",
        type=str,
        default="{}",
        help="JSON string of the AzureOpenAIChatCompletionClient settings for the Meta-Agent.",
    )
    parser.add_argument(
        "--base_agent_model_config",
        type=str,
        default="{}",
        help="JSON string of the AzureOpenAIChatCompletionClient settings for the Base Agent.",
    )
    arguments = parser.parse_args()
    arguments.base_agent_model_config = json.loads(arguments.base_agent_model_config)
    arguments.meta_agent_model_config = json.loads(arguments.meta_agent_model_config)
    if arguments.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("adas.log")
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(arguments))
