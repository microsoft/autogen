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
    OpenAIChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from agnext.components.tools import PythonCodeExecutionTool
from agnext.core import CancellationToken


@dataclass
class ToolMessage:
    function_call: FunctionCall


@dataclass
class ToolResultMessage:
    result: FunctionExecutionResult


@dataclass
class TaskMessage:
    content: str


@dataclass
class LLMResponseMessage:
    content: str


class Coder(TypeRoutedAgent):
    """An agent that uses tools to write, execute, and debug Python code."""

    DEFAULT_DESCRIPTION = "A Python coder assistant."

    DEFAULT_SYSTEM_MESSAGES = [
        SystemMessage("""You are a helpful AI Assistant. Use your tools to solve problems.
                        If the tool results in an error, use the error trace to improve
                        the python code. If the code requires installing packages, use python to install the packages"""),
    ]

    def __init__(
        self,
        model_client: ChatCompletionClient,
        description: str = DEFAULT_DESCRIPTION,
        system_messages: List[SystemMessage] = DEFAULT_SYSTEM_MESSAGES,
    ) -> None:
        super().__init__(description)
        self._model_client = model_client
        self._system_messages = system_messages
        self._tools = [PythonCodeExecutionTool(LocalCommandLineCodeExecutor())]

    @message_handler
    async def handle_user_message(
        self, message: TaskMessage, cancellation_token: CancellationToken
    ) -> LLMResponseMessage:
        """Handle a user message, execute the model and tools, and returns the response."""

        session: List[LLMMessage] = []
        session.append(UserMessage(content=message.content, source="User"))

        response = await self._model_client.create(self._system_messages + session, tools=self._tools)

        session.append(AssistantMessage(content=response.content, source=self.metadata["name"]))

        # Keep executing the tools until the response is not a list of function calls.
        while isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
            results = await asyncio.gather(
                *[self.send_message(ToolMessage(function_call=call), self.id) for call in response.content]
            )
            # Combine the results into a single response.
            result = FunctionExecutionResultMessage(content=[result.result for result in results])
            session.append(result)
            # Execute the model again with the new response.
            response = await self._model_client.create(self._system_messages + session, tools=self._tools)
            session.append(AssistantMessage(content=response.content, source=self.metadata["name"]))

        assert isinstance(response.content, str)
        return LLMResponseMessage(content=response.content)

    @message_handler
    async def handle_tool_call(self, message: ToolMessage, cancellation_token: CancellationToken) -> ToolResultMessage:
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
        return ToolResultMessage(
            result=FunctionExecutionResult(content=result_as_str, call_id=message.function_call.id),
        )


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()

    # Register agents.
    coder = runtime.register_and_get(
        "coder",
        lambda: Coder(model_client=OpenAIChatCompletionClient(model="gpt-4o")),
    )

    task = TaskMessage(input(f"Enter a task for {coder.name}: "))

    # Send a task to the tool user.
    result = runtime.send_message(task, coder)

    # Run the runtime until the task is completed.
    while not result.done():
        await runtime.process_next()

    # Print the result.
    final_response = result.result()
    assert isinstance(final_response, LLMResponseMessage)
    print("--------------------")
    print(final_response.content)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
