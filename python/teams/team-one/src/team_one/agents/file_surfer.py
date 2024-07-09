import asyncio
import json
from pathlib import Path
from typing import List, Tuple

import aiofiles
from agnext.components import FunctionCall, message_handler
from agnext.components.models import (
    ChatCompletionClient,
    FunctionExecutionResult,
    SystemMessage,
)
from agnext.components.tools import FunctionTool
from agnext.core import CancellationToken
from typing_extensions import Annotated

from .base_agent import BaseAgent, UserContent


async def read_local_file(file_path: Annotated[str, "relative or absolute path of file to read"]) -> str:
    """Read contents of a file."""
    try:
        async with aiofiles.open(file_path, mode="r") as file:
            file_contents = str(await file.read())
            return f"""
Here are the contents of the file at path: {file_path}
```
{file_contents}
```
"""

    except FileNotFoundError:
        return f"File not found: {file_path}"


def list_files_and_dirs_like_tree(dir_path: str) -> str:
    """List files and directories in a directory in a format similar to 'tree' command with level 1."""
    path = Path(dir_path)
    if not path.is_dir():
        return f"{dir_path} is not a valid directory."

    items = [f"{dir_path}"]
    for item in path.iterdir():
        if item.is_dir():
            items.append(f"├── {item.name}/")  # Indicate directories with a trailing slash
        else:
            items.append(f"├── {item.name}")  # List files as is
    return "\n".join(items)


class FileSurfer(BaseAgent):
    """An agent that uses tools to read and navigate local files."""

    DEFAULT_DESCRIPTION = "An agent that can handle local files."

    DEFAULT_SYSTEM_MESSAGES = [
        SystemMessage("""
        You are a helpful AI Assistant.
        When given a user query, use available functions to help the user with their request."""),
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
                description="Use this function to read the contents of a local file whose relative or absolute path is given.",
                name="read_local_file",
            ),
            FunctionTool(
                list_files_and_dirs_like_tree,
                description="List files and directories in a directory in a format similar to 'tree' command with level 1",
                name="list_files_and_dirs_like_tree",
            ),
        ]

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        response = await self._model_client.create(self._system_messages + self._chat_history, tools=self._tools)

        if isinstance(response.content, str):
            final_result = response.content

        elif isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
            results = await asyncio.gather(*[self.send_message(call, self.id) for call in response.content])
            for result in results:
                assert isinstance(result, FunctionExecutionResult)
            final_result = "\n".join(result.content for result in results)
        else:
            raise ValueError(f"Unexpected response type: {response.content}")

        assert isinstance(final_result, str)

        return "TERMINATE" in final_result, final_result

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
