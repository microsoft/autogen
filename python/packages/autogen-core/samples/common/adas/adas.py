




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

from autogen_agentchat.agents import CodeExecutorAgent, CodingAssistantAgent
from autogen_core.base import AgentId, AgentType, AgentRuntime, CancellationToken, MessageContext, TopicId
from autogen_core.components import RoutedAgent, default_subscription, message_handler
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.components import DefaultTopicId
from autogen_core.components.models import OpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool, PythonCodeExecutionTool, ToolSchema
from autogen_core.components.tool_agent import ToolAgent, tool_agent_caller_loop
from autogen_ext.code_executors import DockerCommandLineCodeExecutor #, extract_markdown_code_blocks
from autogen_core.components.code_executor import CodeBlock, CodeExecutor, extract_markdown_code_blocks
from autogen_magentic_one.utils import LogHandler
from autogen_core.application.logging import EVENT_LOGGER_NAME

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



@dataclass
class CodeWritingTask:
    task: str


@dataclass
class CodeWritingResult:
    task: str
    code: str
    review: str


@dataclass
class CodeReviewTask:
    session_id: str
    code_writing_task: str
    code_writing_scratchpad: str
    code: str


@dataclass
class CodeReviewResult:
    review: str
    session_id: str
    approved: bool


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


# An agent that makes a direct call to the model, and returns json
class SimpleReflectAgent(RoutedAgent):
    def __init__(self, description: str, model_client: ChatCompletionClient, system_prompt: str) -> None:
        super().__init__(description)
        self._system_messages: List[LLMMessage] = [
            SystemMessage(
                content=system_prompt,
            )
        ]
        self._chat_history: List[LLMMessage] = []
        self._model_client = model_client
        self._cnt = 0

    @message_handler
    async def handle_task(self, message: LLMMessageList, ctx: MessageContext) -> SimpleReflectAgentResponse:
        # logging.info(f"{self._description} received message: {message}")
        # import pdb; pdb.set_trace()
        # model_result = await self._model_client.create(
        #     self._system_messages + self._chat_history + message.llm_message_list
        # )
        print(f"llm_message_list {len(message.llm_message_list)}")
        self._chat_history.extend(message.llm_message_list)

        print(f"-----cnt {self._cnt}")
        print(f"chat history {len(self._chat_history)}")
        self._cnt += 1
        assert isinstance(model_result.content, str)
        json_content = json.loads(model_result.content)
        return SimpleReflectAgentResponse(json_content=json_content)


@dataclass
class Message:
    content: str


@default_subscription
class Assistant(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("An assistant agent.")
        self._model_client = model_client
        self._chat_history: List[LLMMessage] = [
            SystemMessage(
                content="""Write Python script in markdown block, and it will be executed.
Always save figures to file in the current directory. Do not use plt.show()""",
            )
        ]

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        self._chat_history.append(UserMessage(content=message.content, source="user"))
        result = await self._model_client.create(self._chat_history)
        print(f"\n{'-'*80}\nAssistant:\n{result.content}")
        self._chat_history.append(AssistantMessage(content=result.content, source="assistant"))  # type: ignore
        await self.publish_message(Message(content=result.content), DefaultTopicId())  # type: ignore


@default_subscription
class Executor(RoutedAgent):
    def __init__(self, code_executor: CodeExecutor) -> None:
        super().__init__("An executor agent.")
        self._code_executor = code_executor

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        code_blocks = extract_markdown_code_blocks(message.content)
        if code_blocks:
            result = await self._code_executor.execute_code_blocks(
                code_blocks, cancellation_token=ctx.cancellation_token
            )
            print(f"\n{'-'*80}\nExecutor:\n{result.output}")
            await self.publish_message(Message(content=result.output), DefaultTopicId())


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
        # export CHAT_COMPLETION_PROVIDER='azure'


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
    import pdb; pdb.set_trace()
    return acc_list



@default_subscription
class ADASAgent(RoutedAgent):
    """An agent that performs ADAS."""

    def __init__(self,
                 model_client: ChatCompletionClient,
                #  system_prompt: str,
                #  evaluate_agent_type: str,
                 reflect_agent_type: str,
                 executor_agent_type: str,
                 args,
                 archive
        ) -> None:
        super().__init__("An agent searching agent.")
        # self._system_messages: List[LLMMessage] = [
        #     SystemMessage(
        #         content=system_prompt,
        #     )
        # ]
        # self._evaluate_agent_id = AgentId(evaluate_agent_type, self.id.key)
        self._reflect_agent_id = AgentId(reflect_agent_type, self.id.key)
        self._executor_agent_id = AgentId(executor_agent_type, self.id.key)
        self._args = args
        self._archive = archive
        self._model_client = model_client
        self._session_memory: Dict[str, List[ADASTask | ADASResult]] = {}

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
        
        import pdb; pdb.set_trace()
        # Initial prompt
        for n in range(start, args.n_generation):
            print(f"============Generation {n + 1}=================")
            msg_list = [UserMessage(content=message.task, source=self.metadata["type"])]
            import pdb; pdb.set_trace()
            try:
                response = await self.send_message(LLMMessageList(msg_list), self._reflect_agent_id)
                Reflexion_prompt_1, Reflexion_prompt_2 = get_reflexion_prompt(self._archive[-1] if n > 0 else None)

                # Reflexion 1
                next_solution = response.json_content
                new_messages = [
                    AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    UserMessage(content=Reflexion_prompt_1, source=self.metadata["type"]),
                ]
                response = await self.send_message(LLMMessageList(new_messages), AgentId('simple_reflect_agent', self.id.key))

                # Reflexion 2
                next_solution = response.json_content
                new_messages = [
                    AssistantMessage(content=str(next_solution), source=self.metadata["type"]),
                    UserMessage(content=Reflexion_prompt_2, source=self.metadata["type"]),
                ]
                response = await self.send_message(LLMMessageList(new_messages), AgentId('simple_reflect_agent', self.id.key))
            except Exception as e:
                # import pdb; pdb.set_trace()
                print("During LLM generate new solution:")
                print(e)
                continue

        # TODO: Evaluate code
        next_solution = response.json_content
        print(f"final {str(next_solution)}")
        import pdb; pdb.set_trace()
        acc_list = evaluate_forward_fn(args, next_solution["code"])
        import pdb; pdb.set_trace()
    
        print("asdf")
        # TODO: Maybe not... instantiate many agents to run eval.
        # acc_list = await self.send_message(EvaluateTask(), self._evaluate_agent_id)


async def main(args) -> None:
    runtime = SingleThreadedAgentRuntime()
    client = get_chat_completion_client_from_envs(model="gpt-4o-mini")
    archive = get_init_archive()
    system_prompt, prompt = get_prompt(archive)    

    # Create the reflect agent
    await SimpleReflectAgent.register(
        runtime, "simple_reflect_agent", lambda: SimpleReflectAgent(
            description='Simple Reflect Agent',
            model_client=client,
            system_prompt=system_prompt,
        )
    )

    await ADASAgent.register(
        runtime, "adas_agent", lambda: ADASAgent(
            model_client=client,
            args=args,
            archive=archive,
            reflect_agent_type='simple_reflect_agent',
            executor_agent_type='executor',
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
