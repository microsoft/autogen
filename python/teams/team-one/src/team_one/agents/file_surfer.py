import asyncio
import json
from pathlib import Path
from typing import List

import aiofiles
from agnext.components import FunctionCall, TypeRoutedAgent, message_handler
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from agnext.components.tools import FunctionTool
from agnext.core import CancellationToken

from ..messages import LLMResponseMessage, TaskMessage, ToolMessage, ToolResultMessage


async def read_local_file(file_path: str) -> str:
    """Async read the contents of a local file."""
    try:
        async with aiofiles.open(file_path, mode="r") as file:
            return str(await file.read())
    except FileNotFoundError:
        return f"File not found: {file_path}"


def list_files_in_directory(dir_path: str) -> str:
    """List files in a directory asynchronously and return them as a single string."""
    path = Path(dir_path)
    # Joining the file names into a single string separated by new lines
    return "\n".join(item.name for item in path.iterdir() if item.is_file())


class FileSurfer(TypeRoutedAgent):
    """An agent that uses tools to read and navigate local files."""

    DEFAULT_DESCRIPTION = "An agent that can handle local files."

    DEFAULT_SYSTEM_MESSAGES = [
        SystemMessage("""You are a helpful AI Assistant. Use your tools to solve problems
                      that involve reading and navigating files.
                      """),
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
        self._tools = [
            FunctionTool(
                read_local_file,
                description="Read the contents of a local file.",
                name="read_local_file",
            ),
            FunctionTool(
                list_files_in_directory,
                description="Read the contents of a directory",
                name="list_files_in_directory",
            ),
        ]

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
            # TODO: gather internally too
            results = await asyncio.gather(
                *[await self.send_message(ToolMessage(function_call=call), self.id) for call in response.content]
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
