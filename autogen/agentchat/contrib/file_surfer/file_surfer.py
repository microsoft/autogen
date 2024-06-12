import json
import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable, Literal, Tuple

from .... import Agent, ConversableAgent
from ....browser_utils import AbstractMarkdownBrowser, RequestsMarkdownBrowser
from .tool_definitions import *

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


logger = logging.getLogger(__name__)


class FileSurferAgent(ConversableAgent):
    """(In preview) An agent that acts as a basic file surfer that can navigate
    various files. It can open local files, download files, scroll up or down in
    the viewport, find specific words or phrases on the page (ctrl+f), and
    even read the page and answer questions.
    """

    DEFAULT_PROMPT = """
    You are a helpful AI assistant that can navigate local files.
    """

    DEFAULT_DESCRIPTION = """A helpful assistant with access to ability to navigate local files. When asking this agent to open a file, please provide the file's path (relative or absolute). Once the desired file is open, ask this agent to answer questions by reading the file, generate summaries, find specific words or phrases on the page (ctrl+f), or even just scroll up or down in the viewport."""

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List[str]]] = DEFAULT_PROMPT,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        is_termination_msg: Optional[Callable[[Dict[str, Any]], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        browser: Optional[Union[AbstractMarkdownBrowser, None]] = None,
    ):
        self._browser = browser or RequestsMarkdownBrowser(viewport_size=1024 * 5, downloads_folder="coding")

        self.tools = [
            TOOL_OPEN_LOCAL_FILE,
            TOOL_PAGE_UP,
            TOOL_PAGE_DOWN,
            TOOL_FIND_ON_PAGE_CTRL_F,
            TOOL_FIND_NEXT,
        ]

        tool_str = "\n".join([f"{i+1}. {tool['function']['name']}" for i, tool in enumerate(self.tools)])

        system_message += (
            "Choose only between the following tools/function names to satisfy user requests:\n" + tool_str
        )

        super().__init__(
            name=name,
            system_message=system_message,
            description=description,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode="NEVER",
            function_map=None,
            code_execution_config=False,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
        )

        self.register_reply([Agent, None], FileSurferAgent.generate_surfer_reply, remove_other_reply_funcs=True)

    def _get_browser_state(self) -> Tuple[str, str]:
        """
        Get the current state of the browser, including the header and content.
        """
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

    def generate_surfer_reply(
        self,
        messages=None,
        sender=None,
        config=None,
    ):

        history = messages[0 : len(messages) - 1]
        task_contents = messages[-1]["content"]  # the last message from the sender is the task

        context_message = {
            "role": "user",
            "content": "Your browser is currently open to the page '{self._browser.page_title}' at the address '{self._browser.address}'.",
        }

        task_message = {
            "role": "user",
            "content": task_contents,
        }

        history.extend([context_message, task_message])

        response = self.client.create(messages=history, tools=self.tools, tool_choice="auto")

        response = response.choices[0]

        if response.message.content:
            return True, response.message.content

        elif response.message.tool_calls:
            tool_calls = response.message.tool_calls
            for tool_call in tool_calls:
                print(tool_call)
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                self._log_to_console(tool_name, arguments)

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
            return True, final_response

        final_response = "TERMINATE"
        return True, final_response

    def _log_to_console(self, fname, args):
        """Reused from multimodal_web_surfer.py"""
        if fname is None or fname == "":
            fname = "[unknown]"
        if args is None:
            args = {}

        _arg_strs = []
        for a in args:
            _arg_strs.append(a + "='" + str(args[a]) + "'")

        print(
            colored(f"\n>>>>>>>> {self.name} ACTION " + fname + "(" + ", ".join(_arg_strs) + ")", "cyan"),
            flush=True,
        )
