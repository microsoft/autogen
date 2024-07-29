import json
import time
from typing import List, Optional, Tuple

from agnext.components import FunctionCall
from agnext.components.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
)

# from agnext.components.tools import FunctionTool
from agnext.core import CancellationToken

from ...markdown_browser import RequestsMarkdownBrowser
from ..base_worker import BaseWorker

# from typing_extensions import Annotated
from ._tools import TOOL_FIND_NEXT, TOOL_FIND_ON_PAGE_CTRL_F, TOOL_OPEN_LOCAL_FILE, TOOL_PAGE_DOWN, TOOL_PAGE_UP

# async def read_local_file(file_path: Annotated[str, "relative or absolute path of file to read"]) -> str:
#     """Read contents of a file."""
#     try:
#         async with aiofiles.open(file_path, mode="r") as file:
#             file_contents = str(await file.read())
#             return f"""
# Here are the contents of the file at path: {file_path}
# ```
# {file_contents}
# ```
# """

#     except FileNotFoundError:
#         return f"File not found: {file_path}"


# def list_files_and_dirs_like_tree(dir_path: str) -> str:
#     """List files and directories in a directory in a format similar to 'tree' command with level 1."""
#     path = Path(dir_path)
#     if not path.is_dir():
#         return f"{dir_path} is not a valid directory."

#     items = [f"{dir_path}"]
#     for item in path.iterdir():
#         if item.is_dir():
#             items.append(f"├── {item.name}/")  # Indicate directories with a trailing slash
#         else:
#             items.append(f"├── {item.name}")  # List files as is
#     return "\n".join(items)


class FileSurfer(BaseWorker):
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
        browser: Optional[RequestsMarkdownBrowser] = None,
    ) -> None:
        super().__init__(description)
        self._model_client = model_client
        self._system_messages = system_messages
        self._browser = browser
        self._tools = [TOOL_OPEN_LOCAL_FILE, TOOL_PAGE_UP, TOOL_PAGE_DOWN, TOOL_FIND_ON_PAGE_CTRL_F, TOOL_FIND_NEXT]
        # self._tools = [
        #     FunctionTool(
        #         read_local_file,
        #         description="Use this function to read the contents of a local file whose relative or absolute path is given.",
        #         name="read_local_file",
        #     ),
        #     FunctionTool(
        #         list_files_and_dirs_like_tree,
        #         description="List files and directories in a directory in a format similar to 'tree' command with level 1",
        #         name="list_files_and_dirs_like_tree",
        #     ),
        # ]

    def _get_browser_state(self) -> Tuple[str, str]:
        """
        Get the current state of the browser, including the header and content.
        """
        if self._browser is None:
            self._browser = RequestsMarkdownBrowser(viewport_size=1024 * 5, downloads_folder="coding")

        header = f"Address: {self._browser.address}\n"

        if self._browser.page_title is not None:
            header += f"Title: {self._browser.page_title}\n"

        current_page = self._browser.viewport_current_page
        total_pages = len(self._browser.viewport_pages)

        address = self._browser.address
        for i in range(len(self._browser.history) - 2, -1, -1):  # Start from the second last
            if self._browser.history[i][0] == address:
                header += f"You previously visited this page {round(time.time() - self._browser.history[i][1])} seconds ago.\n"
                break

        header += f"Viewport position: Showing page {current_page+1} of {total_pages}.\n"

        return (header, self._browser.viewport)

    # async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:

    #     if self._browser is None:
    #         self._browse = RequestsMarkdownBrowser(viewport_size=1024 * 5, downloads_folder="coding")

    #     response = await self._model_client.create(self._system_messages + self._chat_history, tools=self._tools)

    #     if isinstance(response.content, str):
    #         final_result = response.content

    #     elif isinstance(response.content, list) and all(isinstance(item, FunctionCall) for item in response.content):
    #         results = await asyncio.gather(*[self.send_message(call, self.id) for call in response.content])
    #         for result in results:
    #             assert isinstance(result, FunctionExecutionResult)
    #         final_result = "\n".join(result.content for result in results)
    #     else:
    #         raise ValueError(f"Unexpected response type: {response.content}")

    #     assert isinstance(final_result, str)

    #     return "TERMINATE" in final_result, final_result

    # @message_handler
    # async def handle_tool_call(
    #     self, message: FunctionCall, cancellation_token: CancellationToken
    # ) -> FunctionExecutionResult:
    #     """Handle a tool execution task. This method executes the tool and publishes the result."""
    #     function_call = message
    #     # Find the tool
    #     tool = next((tool for tool in self._tools if tool.name == function_call.name), None)
    #     if tool is None:
    #         result_as_str = f"Error: Tool not found: {function_call.name}"
    #     else:
    #         try:
    #             arguments = json.loads(function_call.arguments)
    #             result = await tool.run_json(args=arguments, cancellation_token=cancellation_token)
    #             result_as_str = tool.return_value_as_string(result)
    #         except json.JSONDecodeError:
    #             result_as_str = f"Error: Invalid arguments: {function_call.arguments}"
    #         except Exception as e:
    #             result_as_str = f"Error: {e}"
    #     return FunctionExecutionResult(content=result_as_str, call_id=function_call.id)

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, str]:
        if self._browser is None:
            self._browser = RequestsMarkdownBrowser(viewport_size=1024 * 5, downloads_folder="coding")

        history = self._chat_history[0:-1]
        last_message = self._chat_history[-1]
        assert isinstance(last_message, UserMessage)

        task_content = last_message.content  # the last message from the sender is the task

        assert self._browser is not None
        # assert self._browser.page_title is not None

        context_message = UserMessage(
            source="user",
            content=f"Your browser is currently open to the page '{self._browser.page_title}' at the address '{self._browser.address}'.",
        )

        task_message = UserMessage(
            source="user",
            content=task_content,
        )

        create_result = await self._model_client.create(
            messages=history + [context_message, task_message], tools=self._tools
        )

        response = create_result.content

        if isinstance(response, str):
            return False, response

        elif isinstance(response, list) and all(isinstance(item, FunctionCall) for item in response):
            function_calls = response
            for function_call in function_calls:
                tool_name = function_call.name
                arguments = json.loads(function_call.arguments)

                if tool_name == "open_local_file":
                    path = arguments["path"]
                    self._browser.open_local_file(path)
                elif tool_name == "page_up":
                    self._browser.page_up()
                elif tool_name == "page_down":
                    self._browser.page_down()
                elif tool_name == "find_on_page_ctrl_f":
                    search_string = arguments["search_string"]
                    self._browser.find_on_page(search_string)
                elif tool_name == "find_next":
                    self._browser.find_next()
            header, content = self._get_browser_state()
            final_response = header.strip() + "\n=======================\n" + content
            return False, final_response

        final_response = "TERMINATE"
        return False, final_response
