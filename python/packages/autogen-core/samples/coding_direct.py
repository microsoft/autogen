"""
This example implements a tool-enabled agent that uses tools to perform tasks.
1. The tool use agent receives a user message, and makes an inference using a model.
If the response is a list of function calls, the tool use agent executes the tools by
sending tool execution task to a tool executor agent.
2. The tool executor agent executes the tools and sends the results back to the
tool use agent, who makes an inference using the model again.
3. The agents keep executing the tools until the inference response is not a
list of function calls.
4. The tool use agent returns the final response to the user.
"""

import asyncio
import os
import sys
from dataclasses import dataclass
from typing import List

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, AgentInstantiationContext
from autogen_core.components import FunctionCall, RoutedAgent, message_handler
from autogen_core.components.code_executor import DockerCommandLineCodeExecutor
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.components.tool_agent import ToolAgent, ToolException
from autogen_core.components.tools import PythonCodeExecutionTool, Tool, ToolSchema

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autogen_core.base import MessageContext
from common.utils import get_chat_completion_client_from_envs


@dataclass
class Message:
    content: str


class ToolUseAgent(RoutedAgent):
    """An agent that uses tools to perform tasks. It executes the tools
    by itself by sending the tool execution task to itself."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        tool_schema: List[ToolSchema],
        tool_agent: AgentId,
    ) -> None:
        super().__init__(description)
        self._model_client = model_client
        self._system_messages = system_messages
        self._tool_schema = tool_schema
        self._tool_agent = tool_agent

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        """Handle a user message, execute the model and tools, and returns the response."""
        session: List[LLMMessage] = []
        session.append(UserMessage(content=message.content, source="User"))
        response = await self._model_client.create(self._system_messages + session, tools=self._tool_schema)
        session.append(AssistantMessage(content=response.content, source=self.metadata["type"]))

        # Keep executing the tools until the response is not a list of function calls.
        while isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
            results: List[FunctionExecutionResult | BaseException] = await asyncio.gather(
                *[
                    self.send_message(call, self._tool_agent, cancellation_token=ctx.cancellation_token)
                    for call in response.content
                ],
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
            response = await self._model_client.create(self._system_messages + session, tools=self._tool_schema)
            session.append(AssistantMessage(content=response.content, source=self.metadata["type"]))

        assert isinstance(response.content, str)
        return Message(content=response.content)


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    async with DockerCommandLineCodeExecutor() as executor:
        # Define the tools.
        tools: List[Tool] = [
            # A tool that executes Python code.
            PythonCodeExecutionTool(
                executor=executor,
            )
        ]
        # Register agents.
        await runtime.register(
            "tool_executor_agent",
            lambda: ToolAgent(
                description="Tool Executor Agent",
                tools=tools,
            ),
        )
        await runtime.register(
            "tool_enabled_agent",
            lambda: ToolUseAgent(
                description="Tool Use Agent",
                system_messages=[SystemMessage("You are a helpful AI Assistant. Use your tools to solve problems.")],
                model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
                tool_schema=[tool.schema for tool in tools],
                tool_agent=AgentId("tool_executor_agent", AgentInstantiationContext.current_agent_id().key),
            ),
        )

        runtime.start()

        # Send a task to the tool user.
        response = await runtime.send_message(
            Message("Run the following Python code: print('Hello, World!')"), AgentId("tool_enabled_agent", "default")
        )
        print(response.content)

        # Run the runtime until the task is completed.
        await runtime.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)
    asyncio.run(main())
