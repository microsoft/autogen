"""
This example implements a tool-enabled agent that uses tools to perform tasks.
1. The agent receives a user message, and makes an inference using a model.
If the response is a list of function calls, the agent executes the tools by
sending tool execution task to itself.
2. The agent executes the tools and sends the results back to itself, and
makes an inference using the model again.
3. The agent keeps executing the tools until the inference response is not a
list of function calls.
4. The agent returns the final response to the user.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import FunctionCall, message_handler
from agnext.components.code_executor import LocalCommandLineCodeExecutor
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from agnext.components.tool_agent import ToolAgent, ToolException
from agnext.components.tools import PythonCodeExecutionTool, Tool
from agnext.core import CancellationToken

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.utils import get_chat_completion_client_from_envs


@dataclass
class Message:
    content: str


class ToolEnabledAgent(ToolAgent):
    """An agent that uses tools to perform tasks. It executes the tools
    by itself by sending the tool execution task to itself."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        tools: List[Tool],
    ) -> None:
        super().__init__(description, tools)
        self._model_client = model_client
        self._system_messages = system_messages

    @message_handler
    async def handle_user_message(self, message: Message, cancellation_token: CancellationToken) -> Message:
        """Handle a user message, execute the model and tools, and returns the response."""
        session: List[LLMMessage] = []
        session.append(UserMessage(content=message.content, source="User"))
        response = await self._model_client.create(self._system_messages + session, tools=self.tools)
        session.append(AssistantMessage(content=response.content, source=self.metadata["name"]))

        # Keep executing the tools until the response is not a list of function calls.
        while isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
            results: List[FunctionExecutionResult | BaseException] = await asyncio.gather(
                *[self.send_message(call, self.id) for call in response.content],
                return_exceptions=True,
            )
            # Combine the results into a single response and handle exceptions.
            function_results: List[FunctionExecutionResult] = []
            for result in results:
                if isinstance(result, FunctionExecutionResult):
                    function_results.append(result)
                elif isinstance(result, ToolException):
                    function_results.append(FunctionExecutionResult(content=f"Error: {result}", call_id=result.call_id))
                elif isinstance(result, BaseException):
                    raise result
            session.append(FunctionExecutionResultMessage(content=function_results))
            # Execute the model again with the new response.
            response = await self._model_client.create(self._system_messages + session, tools=self.tools)
            session.append(AssistantMessage(content=response.content, source=self.metadata["name"]))

        assert isinstance(response.content, str)
        return Message(content=response.content)


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()
    # Define the tools.
    tools: List[Tool] = [
        # A tool that executes Python code.
        PythonCodeExecutionTool(
            LocalCommandLineCodeExecutor(),
        )
    ]
    # Register agents.
    tool_agent = await runtime.register_and_get(
        "tool_enabled_agent",
        lambda: ToolEnabledAgent(
            description="Tool Use Agent",
            system_messages=[SystemMessage("You are a helpful AI Assistant. Use your tools to solve problems.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            tools=tools,
        ),
    )

    run_context = runtime.start()

    # Send a task to the tool user.
    response = await runtime.send_message(Message("Run the following Python code: print('Hello, World!')"), tool_agent)
    print(response.content)

    # Run the runtime until the task is completed.
    await run_context.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
