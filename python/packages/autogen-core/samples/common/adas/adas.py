




import argparse
import asyncio
import os
import logging
import json
import re
import uuid
import pickle
from dataclasses import dataclass
from typing import Dict, List, Union
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import threading
import random
import numpy as np
import requests
from github import Github

from autogen_core.components import RoutedAgent, default_subscription, message_handler
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentType, AgentRuntime, CancellationToken, MessageContext, TopicId
from autogen_core.components import DefaultTopicId
from autogen_core.components.code_executor import CodeBlock, CodeExecutor, extract_markdown_code_blocks
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.components.tool_agent import ToolAgent, tool_agent_caller_loop
from autogen_core.components.tools import FunctionTool, PythonCodeExecutionTool, ToolSchema
from autogen_ext.code_executors import DockerCommandLineCodeExecutor #, extract_markdown_code_blocks
from autogen_magentic_one.utils import LogHandler

# TODO fix imports
import sys
sys.path.append("/home/andyye/autogen/python/packages/autogen-core/samples/")
from common.utils import get_chat_completion_client_from_envs

from adas_prompt import get_init_archive, get_prompt, get_reflexion_prompt
from utils import random_id, bootstrap_confidence_interval, load_drop, drop_metric


logging.basicConfig(level=logging.WARNING)
logging.getLogger("autogen_core").setLevel(logging.DEBUG)

Info = namedtuple('Info', ['name', 'author', 'content', 'iteration_idx'])

SEARCHING_MODE = True


def read_github_file(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return None


def print_repo_contents(repo, path="", indent=""):
    contents = repo.get_contents(path)
    documentation = []
    for content_file in contents:
        if content_file.type == "dir":
            documentation.extend(print_repo_contents(repo, content_file.path, indent + "│   "))
        else:
            if content_file.download_url.endswith('.md'):
                print(f"Reading file from {content_file.download_url}")
                f = read_github_file(content_file.download_url)
                documentation.append("Title: " + content_file.name + "\nContents:\n" + f)
    return documentation


def get_autogen_documentation():
    repo_name = "microsoft/autogen"
    directory_name = "python/packages/autogen-core/docs/src/user-guide/core-user-guide"
    g = Github()

    subdirectories = ['core-concepts', 'framework']
    documentation = []
    for subdir in subdirectories:
        try:
            repo = g.get_repo(repo_name)
            documentation.extend(print_repo_contents(repo, directory_name + '/'+ subdir))
        except Exception as e:
            print(f"Error: {e}")
    print(f"Found {len(documentation)} pages of documentation")
    return documentation


@dataclass
class ADASTask:
    task: str

@dataclass
class ADASResult:
    result: str

@dataclass
class ReflectTask:
    session_id: str
    task: str
    thought: str


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
class LLMAgentBaseResponse:
    output: str


@dataclass
class Message:
    content: str


class AgentSystem():
    def __init__(self) -> None:
        pass

def generate_task(input_infos) -> str:

    # construct input infos text
    input_infos_text = ''
    for input_info in input_infos:
        if isinstance(input_info, Info):
            (field_name, author, content, iteration_idx) = input_info
        else:
            continue

        if field_name == 'task':
            input_infos_text += f'# Your Task:\n{content}\n\n'
        elif iteration_idx != -1:
            # input_infos_text += f'### {field_name} #{iteration_idx + 1} by {author}:\n{content}\n\n'
            input_infos_text += f'### {field_name} #{iteration_idx + 1}:\n{content}\n\n'
        else:
            # input_infos_text += f'### {field_name} by {author}:\n{content}\n\n'
            input_infos_text += f'### {field_name}:\n{content}\n\n'

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
    examples = load_drop(args.data_filename)[1:-1]  # first one and the last one is for few-shot examples
    random.seed(args.shuffle_seed)
    random.shuffle(examples)

    if SEARCHING_MODE:
        examples = examples[:args.valid_size] * args.n_repeat
    else:
        examples = examples[args.valid_size:args.valid_size + args.test_size] * args.n_repeat

    questions = [example['inputs'] for example in examples]
    answers = [example['targets'] for example in examples]

    print(f"problem length: {len(examples)}")
    max_workers = min(len(examples), args.max_workers) if args.multiprocessing else 1

    task_queue = []
    for q in questions:
        taskInfo = Info('task', 'User', q, -1)
        task_queue.append((taskInfo, AgentSystem()))

    # agentSystem = AgentSystem()

    def call_forward(agent_task_queue):
        taskInfo, agent = agent_task_queue
        print(f"taskInfo {taskInfo}")
        task = generate_task([taskInfo])

        # For magentic one using the create_completion_client_from_env() helper
        agent_model_kwargs = {}

        result = agent.forward(task, agent_model_kwargs)
        return result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(tqdm(executor.map(call_forward, task_queue), total=len(task_queue)))

    acc_list = []
    for q_idx, res in enumerate(results):
        try:
            if isinstance(res, Info):
                extracted_answer = res.content
            else:
                extracted_answer = res
            correct_answers = answers[q_idx]
            print(f"extracted_answer {extracted_answer}, correct_answers {correct_answers}")
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

    def __init__(self,
                 model_client: ChatCompletionClient,
                 system_prompt: str,
                 args,
                 archive
        ) -> None:
        super().__init__("An agent searching agent.")
        # self._system_messages: List[LLMMessage] = [
        #     SystemMessage(
        #         content=system_prompt,
        #     )
        # ]

        self._args = args
        self._archive = archive
        self._model_client = model_client
        self._session_memory: Dict[str, List[ADASTask | ADASResult]] = {}

        # TODO(yeandy): Add this as a proper Tool https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/framework/tools.html
        # pip install pygithub
        self._documentation = get_autogen_documentation()

        self._system_messages: List[LLMMessage] = [
            SystemMessage(
                content=system_prompt('\n'.join(self._documentation)),
            )
        ]
        self._chat_history: List[LLMMessage] = []
        self._model_client = model_client
        self._cnt = 0

    @message_handler
    async def handle_task(self, message: LLMMessageList, ctx: MessageContext) -> SimpleReflectAgentResponse:
        logging.info(f"{self._description} received message: {message}")
        model_result = await self._model_client.create(
            # self._system_messages + self._chat_history + message.llm_message_list
            self._system_messages + message.llm_message_list

        )
        print(f"llm_message_list {len(message.llm_message_list)}")
        # self._chat_history.extend(message.llm_message_list)

        print(f"-----cnt {self._cnt}")
        # print(f"chat history {len(self._chat_history)}")
        self._cnt += 1
        assert isinstance(model_result.content, str)
        print(f"model_result.content {model_result.content}")
        json_content = json.loads(model_result.content)
        print(f"finish converting to json")
        return SimpleReflectAgentResponse(json_content=json_content)

    @message_handler
    async def handle_adas_task(self, message: ADASTask, ctx: MessageContext) -> None:
        # Store the messages in a temporary memory for this request only.
        session_id = str(uuid.uuid4())
        self._session_memory.setdefault(session_id, []).append(message)

        # Process archive
        file_path = os.path.join(args.save_dir, f"{args.expr_name}_run_archive.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                archive = json.load(json_file)
            if "generation" in archive[-1] and isinstance(archive[-1]['generation'], int):
                start = archive[-1]['generation']
            else:
                start = 0
        else:
            archive = get_init_archive()
            start = 0

        for solution in archive:
            if 'fitness' in solution:
                continue

            solution['generation'] = "initial"
            print(f"============Initial Archive: {solution['name']}=================")
            try:
                acc_list = evaluate_forward_fn(args, solution["code"])
            except Exception as e:
                print("During evaluating initial archive:")
                print(e)
                continue

            fitness_str = bootstrap_confidence_interval(acc_list)
            solution['fitness'] = fitness_str

            # save results
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as json_file:
                json.dump(archive, json_file, indent=4)
        
        # Initial prompt
        for n in range(start, args.n_generation):
            print(f"============Generation {n + 1}=================")
            msg_list = [UserMessage(content=message.task, source=self.metadata["type"])]
            import pdb; pdb.set_trace()
            try:
                response = await self.send_message(LLMMessageList(msg_list), self.id)
                next_solution = response.json_content
                Reflexion_prompt_1, Reflexion_prompt_2 = get_reflexion_prompt(self._archive[-1] if n > 0 else None)
                print(f"Reflexion_prompt_1 {Reflexion_prompt_1}")
                print(f"Reflexion_prompt_2 {Reflexion_prompt_2}")
                print(f"@@After initial prompt {response}")

                # Reflexion 1
                # new_messages = [
                #     AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                #     UserMessage(content=Reflexion_prompt_1, source=self.metadata["type"]),
                # ]
                new_messages = msg_list + [
                    AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    UserMessage(content=Reflexion_prompt_1, source=self.metadata["type"]),
                ]
                response = await self.send_message(LLMMessageList(new_messages), self.id)
                next_solution = response.json_content
                print(f"@@After Reflexion_prompt_1 {response}")

                # Reflexion 2
                # new_messages = [
                #     AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                #     UserMessage(content=Reflexion_prompt_2, source=self.metadata["type"]),
                # ]
                new_messages = new_messages + [
                    AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    UserMessage(content=Reflexion_prompt_2, source=self.metadata["type"]),
                ]
                response = await self.send_message(LLMMessageList(new_messages), self.id)
                next_solution = response.json_content
                # next_solution = {'reflection': 'The previous code attempted to implement an ensemble approach with additional confidence estimation, but there were errors that needed addressing. Specifically:\n1. **Incorrect Use of `publish_message`:** The previously provided code misuses `self.publish_message()` in a context where the function signature might be misleading, as it requires `None` as its return.\n2. **Improper Handling of Topics and Message Types:** The correct usage for publishing and handling message types is essential, utilizing the proper `TopicId` syntax.\n3. **Incorrect Method for Calculating Confidence:** The confidence estimation implementation was overly simplistic, which could lead to skewed results. \n\nThe revised implementation corrects these issues and ensures compliance with best practices.', 'thought': '**Insights:**\nThe next iteration of the agent should refine on the concept of diversified reasoning by incorporating evaluative mechanisms within Worker Agents to self-assess their response confidence and determine when consensus should be approached collaboratively.\n\n**Overall Idea:**\nThe architecture can further benefit from introducing adaptive learning patterns, where Worker Agents adjust their reasoning strategies dynamically based on prior task ratings or other metadata. This enables a feedback loop that improves over time.\n\n**Implementation:**\n- Modify Worker Agents to give confidence ratings in their output.\n- Integrate an orchestrator that places more weight on outputs with higher confidence when synthesizing results.\n- Ensure message handling aligns with idiomatic usage of message types and topics, using `TopicId` properly.', 'name': 'Adaptive Diverse Ensemble', 'code': 'def forward(self, task, model_client_kwargs):\n    import asyncio\n    from dataclasses import dataclass\n    from typing import List\n    from collections import Counter\n    from autogen_core.base import MessageContext, AgentId, AgentRuntime, TopicId\n    from autogen_core.components import RoutedAgent, message_handler, ClosureAgent, TypeSubscription\n    from autogen_core.components.models import ChatCompletionClient, LLMMessage, SystemMessage, UserMessage\n    from autogen_core.application import SingleThreadedAgentRuntime\n    from autogen_ext.models import AzureOpenAIChatCompletionClient\n    from azure.identity import DefaultAzureCredential, get_bearer_token_provider\n\n    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")\n\n    # Create an AzureOpenAI model client.\n    model_client = AzureOpenAIChatCompletionClient(\n        model=model_client_kwargs[\'model\'],\n        api_version=model_client_kwargs[\'api_version\'],\n        azure_endpoint=model_client_kwargs[\'azure_endpoint\'],\n        azure_ad_token_provider=token_provider,\n        model_capabilities={\n            "vision": True,\n            "function_calling": True,\n            "json_output": True,\n        },\n    )\n\n    @dataclass\n    class DiverseThoughtTask:\n        task: str\n\n    @dataclass\n    class DiverseThoughtResult:\n        result: str\n        confidence: float\n\n    # Define Diverse Worker Agent\n    class DiverseWorkerAgent(RoutedAgent):\n        def __init__(self, description: str, model_client: ChatCompletionClient, instruction: str) -> None:\n            super().__init__(description)\n            self._model_client = model_client\n            self._instruction = instruction\n\n        @message_handler\n        async def handle_task(self, message: DiverseThoughtTask, ctx: MessageContext) -> None:\n            user_prompt = message.task + "\\n" + self._instruction\n            model_result = await self._model_client.create([UserMessage(content=user_prompt, source="worker_agent")])\n            confidence = self.estimate_confidence(model_result.content)\n            assert isinstance(model_result.content, str)\n            await self.publish_message(DiverseThoughtResult(result=model_result.content, confidence=confidence), \n                                       topic_id=TopicId("worker_results", self.id.key))\n\n        def estimate_confidence(self, text: str) -> float:\n            # Improved placeholder for actual confidence estimation method\n            # Here, we can use sentiment analysis or other processing as an example\n            return min(1.0, max(0.0, len(text) / 100.0))\n\n    # Orchestrator Agent for Consensus\n    class OrchestratorAgent(RoutedAgent):\n        def __init__(self) -> None:\n            super().__init__("Orchestrator for Diverse Thoughts")\n\n        @message_handler\n        async def handle_task(self, message: DiverseThoughtTask, ctx: MessageContext) -> None:\n            worker_ids = [AgentId("worker_1", ctx.id.key), AgentId("worker_2", ctx.id.key), AgentId("worker_3", ctx.id.key)]\n            results = await asyncio.gather(*[self.send_message(message, worker_id) for worker_id in worker_ids])\n            combined_result = self.evaluate_results(results)\n            await self.publish_message(DiverseThoughtResult(result=combined_result, confidence=1.0), \n                                       topic_id=TopicId("diverse_result", "orchestrator"))\n\n        def evaluate_results(self, results: List[DiverseThoughtResult]) -> str:\n            # Implement advanced evaluation, here just demonstrating a weighted result selection based on confidence\n            confidences = Counter()\n            for res in results:\n                confidences[res.result] += res.confidence\n            return max(confidences, key=confidences.get)\n\n    async def main():\n        # Create a queue to collect final answers\n        queue = asyncio.Queue[DiverseThoughtResult]()\n        async def output_result(_runtime: AgentRuntime, id: AgentId, message: DiverseThoughtResult, ctx: MessageContext) -> None:\n            await queue.put(message)\n\n        # Initialize the agent runtime\n        runtime = SingleThreadedAgentRuntime()\n\n        # Register workers with various strategies\n        strategies = ["utilize strict logical reasoning", "incorporate probabilistic reasoning", "focus on evidence-based reasoning"]\n        for i, strat in enumerate(strategies, start=1):\n            await DiverseWorkerAgent.register(\n                runtime, f"worker_{i}", lambda strat=strat: DiverseWorkerAgent(\n                    description=f"Diverse Worker {i}", model_client=model_client, instruction=strat\n                )\n            )\n\n        # Register Orchestrator\n        await OrchestratorAgent.register(runtime, "orchestrator")\n\n        # Create closure agent to collect final output result\n        result_topic = TypeSubscription(topic_type="diverse_result", agent_type="output_result")\n        await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [result_topic])\n\n        # Start the runtime, and publish the first message\n        runtime.start()\n        await runtime.publish_message(\n            message=DiverseThoughtTask(task=task),\n            topic_id=TopicId("diverse", "orchestrator")\n        )\n\n        # Keep processing messages until idle.\n        await runtime.stop_when_idle()\n\n        # Return the first answer from the queue\n        return (await queue.get()).result\n\n    return asyncio.run(main())\n'}
                print(f"@@After Reflexion_prompt_2 {next_solution}")
            except Exception as e:
                # import pdb; pdb.set_trace()
                print("During LLM generate new solution:")
                print(e)
                import pdb; pdb.set_trace()
                n -= 1
                continue

            import pdb; pdb.set_trace()
            acc_list = []
            for _ in range(args.debug_max):
                print(f"DEBUGGING")
                try:
                    acc_list = evaluate_forward_fn(args, next_solution["code"])
                    if np.mean(acc_list) < 0.01 and SEARCHING_MODE:
                        raise Exception("All 0 accuracy")
                    break
                except Exception as e:
                    print("During evaluation:")
                    print(e)
                    next_solution = response.json_content
                    # new_messages = [
                    #     AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    #     UserMessage(content=f"Error during evaluation:\n{e}\nCarefully consider where you went wrong in your latest implementation. Using insights from previous attempts, try to debug the current code to implement the same thought. Repeat your previous thought in 'thought', and put your thinking for debugging in 'debug_thought'", source=self.metadata["type"]),
                    # ]
                    new_messages = new_messages + [
                        AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                        UserMessage(content=f"Error during evaluation:\n{e}\nCarefully consider where you went wrong in your latest implementation. Using insights from previous attempts, try to debug the current code to implement the same thought. Repeat your previous thought in 'thought', and put your thinking for debugging in 'debug_thought'", source=self.metadata["type"]),
                    ]
                    try:
                        response = await self.send_message(LLMMessageList(new_messages), self.id)
                        next_solution = response.json_content
                    except Exception as e:
                        print("During LLM generate new solution:")
                        print(e)
                        import pdb; pdb.set_trace()
                        continue
                    continue
            if not acc_list:
                n -= 1
                continue

            import pdb; pdb.set_trace()
            fitness_str = bootstrap_confidence_interval(acc_list)
            next_solution['fitness'] = fitness_str
            next_solution['generation'] = n + 1

            if 'debug_thought' in next_solution:
                del next_solution['debug_thought']
            if 'reflection' in next_solution:
                del next_solution['reflection']
            archive.append(next_solution)

            # save results
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as json_file:
                json.dump(archive, json_file, indent=4)

async def main(args) -> None:
    runtime = SingleThreadedAgentRuntime()
    client = get_chat_completion_client_from_envs(model="gpt-4o-mini")
    archive = get_init_archive()
    system_prompt, prompt = get_prompt(archive)    

    await ADASAgent.register(
        runtime, "adas_agent", lambda: ADASAgent(
            model_client=client,
            system_prompt=system_prompt,
            args=args,
            archive=archive,
        )
    )
    
    runtime.start()

    # Publish an initial message to trigger the ADAS search to start.
    await runtime.publish_message(
        message=ADASTask(task=prompt),
        topic_id=DefaultTopicId(),
    )

    # Keep processing messages until idle.
    await runtime.stop_when_idle()


# python packages/autogen-core/samples/common/adas/adas.py --data_filename=/home/andyye/ADAS/dataset/drop_v0_dev.jsonl.gz --valid_size=1
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ADAS")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument('--data_filename', type=str, default="dataset/drop_v0_dev.jsonl.gz")
    parser.add_argument('--valid_size', type=int, default=128)
    parser.add_argument('--test_size', type=int, default=800)
    parser.add_argument('--shuffle_seed', type=int, default=0)
    parser.add_argument('--n_repeat', type=int, default=1)
    parser.add_argument('--multiprocessing', action='store_true', default=True)
    parser.add_argument('--max_workers', type=int, default=48)
    parser.add_argument('--debug', action='store_true', default=True)
    parser.add_argument('--save_dir', type=str, default='results/')
    parser.add_argument('--expr_name', type=str, default="drop_gpt3.5_results")
    parser.add_argument('--n_generation', type=int, default=30)
    parser.add_argument('--debug_max', type=int, default=3)
    parser.add_argument('--model',
                        type=str,
                        default='gpt-4o-2024-05-13',
                        choices=['gpt-4-turbo-2024-04-09', 'gpt-3.5-turbo-0125', 'gpt-4o-2024-05-13'])
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("adas.log")
        logging.getLogger("autogen_core").addHandler(handler)

    asyncio.run(main(args))
