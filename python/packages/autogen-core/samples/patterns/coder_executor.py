"""
This example shows how to use publish-subscribe to implement
a simple interaction between a coder and an executor agent.
1. The coder agent receives a task message, generates a code block,
and publishes a code execution
task message.
2. The executor agent receives the code execution task message,
executes the code block, and publishes a code execution task result message.
3.  The coder agent receives the code execution task result message, depending
on the result: if the task is completed, it publishes a task completion message;
otherwise, it generates a new code block and publishes a code execution task message.
4. The process continues until the coder agent publishes a task completion message.
"""

import asyncio
import os
import re
import sys
import uuid
from dataclasses import dataclass
from typing import Dict, List

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.components import DefaultSubscription, DefaultTopicId, RoutedAgent, message_handler
from autogen_core.components.code_executor import CodeBlock, CodeExecutor, DockerCommandLineCodeExecutor
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autogen_core.base import MessageContext
from common.utils import get_chat_completion_client_from_envs


@dataclass
class TaskMessage:
    content: str


@dataclass
class TaskCompletion:
    content: str


@dataclass
class CodeExecutionTask:
    session_id: str
    content: str


@dataclass
class CodeExecutionTaskResult:
    session_id: str
    output: str
    exit_code: int


class Coder(RoutedAgent):
    """An agent that writes code."""

    def __init__(
        self,
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__(description="A Python coder assistant.")
        self._model_client = model_client
        self._system_messages = [
            SystemMessage(
                """You are a helpful AI assistant.
Solve tasks using your coding and language skills.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
Reply "TERMINATE" in the end when everything is done."""
            )
        ]
        # A dictionary to store the messages for each task session.
        self._session_memory: Dict[str, List[LLMMessage]] = {}

    @message_handler
    async def handle_task(self, message: TaskMessage, ctx: MessageContext) -> None:
        # Create a new session.
        session_id = str(uuid.uuid4())
        self._session_memory.setdefault(session_id, []).append(UserMessage(content=message.content, source="user"))

        # Make an inference to the model.
        response = await self._model_client.create(self._system_messages + self._session_memory[session_id])
        assert isinstance(response.content, str)
        self._session_memory[session_id].append(
            AssistantMessage(content=response.content, source=self.metadata["type"])
        )

        # Publish the code execution task.
        await self.publish_message(
            CodeExecutionTask(content=response.content, session_id=session_id),
            cancellation_token=ctx.cancellation_token,
            topic_id=DefaultTopicId(),
        )

    @message_handler
    async def handle_code_execution_result(self, message: CodeExecutionTaskResult, ctx: MessageContext) -> None:
        # Store the code execution output.
        self._session_memory[message.session_id].append(UserMessage(content=message.output, source="user"))

        # Make an inference to the model -- reflection on the code execution output happens here.
        response = await self._model_client.create(self._system_messages + self._session_memory[message.session_id])
        assert isinstance(response.content, str)
        self._session_memory[message.session_id].append(
            AssistantMessage(content=response.content, source=self.metadata["type"])
        )

        if "TERMINATE" in response.content:
            # If the task is completed, publish a message with the completion content.
            await self.publish_message(
                TaskCompletion(content=response.content),
                cancellation_token=ctx.cancellation_token,
                topic_id=DefaultTopicId(),
            )
            print("--------------------")
            print("Task completed:")
            print(response.content)
            return

        # Publish the code execution task.
        await self.publish_message(
            CodeExecutionTask(content=response.content, session_id=message.session_id),
            cancellation_token=ctx.cancellation_token,
            topic_id=DefaultTopicId(),
        )


class Executor(RoutedAgent):
    """An agent that executes code."""

    def __init__(self, executor: CodeExecutor) -> None:
        super().__init__(description="A code executor agent.")
        self._executor = executor

    @message_handler
    async def handle_code_execution(self, message: CodeExecutionTask, ctx: MessageContext) -> None:
        # Extract the code block from the message.
        code_blocks = self._extract_code_blocks(message.content)
        if not code_blocks:
            # If no code block is found, publish a message with an error.
            await self.publish_message(
                CodeExecutionTaskResult(
                    output="Error: no Markdown code block found.", exit_code=1, session_id=message.session_id
                ),
                cancellation_token=ctx.cancellation_token,
                topic_id=DefaultTopicId(),
            )
            return
        # Execute code blocks.
        result = await self._executor.execute_code_blocks(
            code_blocks=code_blocks, cancellation_token=ctx.cancellation_token
        )
        # Publish the code execution result.
        await self.publish_message(
            CodeExecutionTaskResult(output=result.output, exit_code=result.exit_code, session_id=message.session_id),
            cancellation_token=ctx.cancellation_token,
            topic_id=DefaultTopicId(),
        )

    def _extract_code_blocks(self, markdown_text: str) -> List[CodeBlock]:
        pattern = re.compile(r"```(?:\s*([\w\+\-]+))?\n([\s\S]*?)```")
        matches = pattern.findall(markdown_text)
        code_blocks: List[CodeBlock] = []
        for match in matches:
            language = match[0].strip() if match[0] else ""
            code_content = match[1]
            code_blocks.append(CodeBlock(code=code_content, language=language))
        return code_blocks


async def main(task: str, temp_dir: str) -> None:
    # Create the runtime with the termination handler.
    runtime = SingleThreadedAgentRuntime()

    async with DockerCommandLineCodeExecutor(work_dir=temp_dir) as executor:
        # Register the agents.
        await runtime.register(
            "coder",
            lambda: Coder(model_client=get_chat_completion_client_from_envs(model="gpt-4-turbo")),
            lambda: [DefaultSubscription()],
        )
        await runtime.register(
            "executor",
            lambda: Executor(executor=executor),
            lambda: [DefaultSubscription()],
        )
        runtime.start()

        # Publish the task message.
        await runtime.publish_message(TaskMessage(content=task), topic_id=DefaultTopicId())

        await runtime.stop_when_idle()


if __name__ == "__main__":
    import logging
    from datetime import datetime

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)

    task = f"Today is {datetime.today()}, create a plot of NVDA and TSLA stock prices YTD using yfinance."

    asyncio.run(main(task, "."))
