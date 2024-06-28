import asyncio
import copy
import json
from pathlib import Path
from typing import List

import aiofiles
from agnext.components import FunctionCall, TypeRoutedAgent, message_handler
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from agnext.components.tools import FunctionTool
from agnext.core import CancellationToken

from ..messages import BroadcastMessage, RequestReplyMessage


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
        self._history: List[LLMMessage] = []

    @message_handler
    async def on_broadcast_message(self, message: BroadcastMessage, cancellation_token: CancellationToken) -> None:
        """Handle a user message, execute the model and tools, and returns the response."""
        assert isinstance(message.content, UserMessage)
        self._history.append(message.content)

    @message_handler
    async def on_request_reply_message(
        self, message: RequestReplyMessage, cancellation_token: CancellationToken
    ) -> None:
        session: List[LLMMessage] = copy.deepcopy(self._history)

        response = await self._model_client.create(self._system_messages + session, tools=self._tools)
        session.append(AssistantMessage(content=response.content, source=self.metadata["name"]))

        if isinstance(response.content, str):
            final_result = response.content

        elif isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
            results = await asyncio.gather(*[await self.send_message(call, self.id) for call in response.content])
            for result in results:
                assert isinstance(result, FunctionExecutionResult)
            final_result = "\n".join(result.content for result in results)
        else:
            raise ValueError(f"Unexpected response type: {response.content}")

        assert isinstance(final_result, str)

        session.append(AssistantMessage(content=final_result, source=self.metadata["name"]))
        await self.publish_message(
            BroadcastMessage(content=UserMessage(content=final_result, source=self.metadata["name"]))
        )

    @message_handler
    async def handle_tool_call(
        self, message: FunctionCall, cancellation_token: CancellationToken
    ) -> FunctionExecutionResult:
        """Handle a tool execution task. This method executes the tool and publishes the result."""
        function_call = message
        # Find the tool
        tool = next((tool for tool in self._tools if tool.name == function_call.name), None)
        if tool is None:
            result_as_str = f"Error: Tool not found: {function_call.name}"
        else:
            try:
                arguments = json.loads(function_call.arguments)
                result = await tool.run_json(args=arguments, cancellation_token=cancellation_token)
                result_as_str = tool.return_value_as_string(result)
            except json.JSONDecodeError:
                result_as_str = f"Error: Invalid arguments: {function_call.arguments}"
            except Exception as e:
                result_as_str = f"Error: {e}"
        return FunctionExecutionResult(content=result_as_str, call_id=function_call.id)
