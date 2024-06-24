import asyncio
import json
from dataclasses import dataclass
from typing import List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import FunctionCall, TypeRoutedAgent, message_handler
from agnext.components.code_executor import LocalCommandLineCodeExecutor
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    OpenAI,
    SystemMessage,
    UserMessage,
)
from agnext.components.tools import PythonCodeExecutionTool, Tool
from agnext.core import AgentId, CancellationToken


@dataclass
class ToolExecutionTask:
    function_call: FunctionCall


@dataclass
class ToolExecutionTaskResult:
    result: FunctionExecutionResult


@dataclass
class UserRequest:
    content: str


@dataclass
class AIResponse:
    content: str


class ToolExecutorAgent(TypeRoutedAgent):
    """An agent that executes tools."""

    def __init__(self, description: str, tools: List[Tool]) -> None:
        super().__init__(description)
        self._tools = tools

    @message_handler
    async def handle_tool_call(
        self, message: ToolExecutionTask, cancellation_token: CancellationToken
    ) -> ToolExecutionTaskResult:
        """Handle a tool execution task. This method executes the tool and publishes the result."""
        # Find the tool
        tool = next((tool for tool in self._tools if tool.name == message.function_call.name), None)
        if tool is None:
            result_as_str = f"Error: Tool not found: {message.function_call.name}"
        else:
            try:
                arguments = json.loads(message.function_call.arguments)
                result = await tool.run_json(args=arguments, cancellation_token=cancellation_token)
                result_as_str = tool.return_value_as_string(result)
            except json.JSONDecodeError:
                result_as_str = f"Error: Invalid arguments: {message.function_call.arguments}"
            except Exception as e:
                result_as_str = f"Error: {e}"
        return ToolExecutionTaskResult(
            result=FunctionExecutionResult(content=result_as_str, call_id=message.function_call.id),
        )


class ToolUserAgent(TypeRoutedAgent):
    """An agent that uses tools to perform tasks. It doesn't execute the tools
    by itself, but delegates the execution to ToolExecutorAgent using direct
    messaging."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        tools: List[Tool],
        tool_executor: AgentId,
    ) -> None:
        super().__init__(description)
        self._model_client = model_client
        self._system_messages = system_messages
        self._tools = tools
        self._tool_executor = tool_executor

    @message_handler
    async def handle_user_message(self, message: UserRequest, cancellation_token: CancellationToken) -> AIResponse:
        """Handle a user message, execute the model and tools, and returns the response."""
        session: List[LLMMessage] = []
        session.append(UserMessage(content=message.content, source="User"))
        response = await self._model_client.create(self._system_messages + session, tools=self._tools)
        session.append(AssistantMessage(content=response.content, source=self.metadata["name"]))

        # Keep executing the tools until the response is not a list of function calls.
        while isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
            results = await asyncio.gather(
                *[
                    self.send_message(ToolExecutionTask(function_call=call), self._tool_executor)
                    for call in response.content
                ]
            )
            # Combine the results into a single response.
            result = FunctionExecutionResultMessage(content=[result.result for result in results])
            session.append(result)
            # Execute the model again with the new response.
            response = await self._model_client.create(self._system_messages + session, tools=self._tools)
            session.append(AssistantMessage(content=response.content, source=self.metadata["name"]))

        assert isinstance(response.content, str)
        return AIResponse(content=response.content)


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
    executor = runtime.register_and_get("tool_executor", lambda: ToolExecutorAgent("Tool Executor", tools))
    tool_user = runtime.register_and_get(
        "tool_use_agent",
        lambda: ToolUserAgent(
            description="Tool Use Agent",
            system_messages=[SystemMessage("You are a helpful AI Assistant. Use your tools to solve problems.")],
            model_client=OpenAI(model="gpt-3.5-turbo"),
            tools=tools,
            tool_executor=executor,
        ),
    )

    # Send a task to the tool user.
    result = runtime.send_message(UserRequest("Run the following Python code: print('Hello, World!')"), tool_user)

    # Run the runtime until the task is completed.
    while not result.done():
        await runtime.process_next()

    # Print the result.
    ai_response = result.result()
    assert isinstance(ai_response, AIResponse)
    print(ai_response.content)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
