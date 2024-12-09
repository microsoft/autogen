import json
import time
from typing import List, Optional, Tuple

from autogen_core import CancellationToken, FunctionCall, default_subscription
from autogen_core.components.models import (
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
)

from ...markdown_browser import RequestsMarkdownBrowser
from ..base_worker import BaseWorker

# from typing_extensions import Annotated
from ._tools import TOOL_FIND_NEXT, TOOL_FIND_ON_PAGE_CTRL_F, TOOL_OPEN_LOCAL_FILE, TOOL_PAGE_DOWN, TOOL_PAGE_UP


@default_subscription
class FileSurfer(BaseWorker):
    """An agent that uses tools to read and navigate local files."""

    DEFAULT_DESCRIPTION = "An agent that can handle local files."

    DEFAULT_SYSTEM_MESSAGES = [
        SystemMessage(
            content="""
        You are a helpful AI Assistant.
        When given a user query, use available functions to help the user with their request."""
        ),
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

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, str]:
        if self._browser is None:
            self._browser = RequestsMarkdownBrowser(viewport_size=1024 * 5, downloads_folder="coding")

        history = self._chat_history[0:-1]
        last_message = self._chat_history[-1]
        assert isinstance(last_message, UserMessage)

        task_content = last_message.content  # the last message from the sender is the task

        assert self._browser is not None

        context_message = UserMessage(
            source="user",
            content=f"Your browser is currently open to the page '{self._browser.page_title}' at the address '{self._browser.address}'.",
        )

        task_message = UserMessage(
            source="user",
            content=task_content,
        )

        create_result = await self._model_client.create(
            messages=history + [context_message, task_message], tools=self._tools, cancellation_token=cancellation_token
        )

        response = create_result.content

        if isinstance(response, str):
            return False, response

        elif isinstance(response, list) and all(isinstance(item, FunctionCall) for item in response):
            function_calls = response
            for function_call in function_calls:
                tool_name = function_call.name

                try:
                    arguments = json.loads(function_call.arguments)
                except json.JSONDecodeError as e:
                    error_str = f"File surfer encountered an error decoding JSON arguments: {e}"
                    return False, error_str

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
