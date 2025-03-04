import inspect
import json
import os
import shutil
from typing import Any, Dict, List, Mapping, Optional, Sequence, TypedDict

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import AgentEvent, ChatMessage
from autogen_core import Image
from autogen_core.models import (
    AssistantMessage,
    CreateResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    RequestUsage,
    SystemMessage,
    UserMessage,
)

from ._functions import MessageContent, hash_directory


def _html_opening(file_title: str, finished: bool = False) -> str:
    """
    Returns the opening text of a simple HTML file.
    """
    refresh_tag = '<meta http-equiv="refresh" content="2">' if not finished else ""
    st = f"""
    <!DOCTYPE html>
    <html>
    <head>
        {refresh_tag}
        <title>{file_title}</title>
        <style>
            body {{font-size: 20px}}
            body {{white-space: pre-wrap}}
        </style>
    </head>
    <body>"""
    return st


def _html_closing() -> str:
    """
    Return the closing text of a simple HTML file.
    """
    return """</body></html>"""


# Following the nested-config pattern, this TypedDict minimizes code changes by encapsulating
# the settings that change frequently, as when loading many settings from a single YAML file.
class PageLoggerConfig(TypedDict, total=False):
    level: str
    path: str


class PageLogger:
    """
    Logs text and images to a set of HTML pages, one per function/method, linked to each other in a call tree.

    Args:
        config: An optional dict that can be used to override the following values:

            - level: The logging level, one of DEBUG, INFO, WARNING, ERROR, CRITICAL, or NONE.
            - path: The path to the directory where the log files will be written.
    """

    def __init__(self, config: PageLoggerConfig | None = None) -> None:
        self.levels = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
            "NONE": 100,
        }

        # Apply default settings and any config overrides.
        level_str = "NONE"  # Default to no logging at all.
        self.log_dir = "./pagelogs/default"
        if config is not None:
            level_str = config.get("level", level_str)
            self.log_dir = config.get("path", self.log_dir)
        self.level = self.levels[level_str]
        self.log_dir = os.path.expanduser(self.log_dir)

        # If the logging level is set to NONE or higher, don't log anything.
        if self.level >= self.levels["NONE"]:
            return

        self.page_stack = PageStack()
        self.pages: List[Page] = []
        self.last_page_id = 0
        self.name = "0  Call Tree"
        self._create_run_dir()
        self.flush()
        self.finalized = False

    def __del__(self) -> None:
        self.finalize()

    def finalize(self) -> None:
        # Writes a hash of the log directory to a file for change detection.
        if self.level >= self.levels["NONE"]:
            return

        # Don't finalize the log if it has already been finalized.
        if self.finalized:
            return

        # Do nothing if the app is being forced to exit early.
        if self.page_stack.size() > 0:
            return

        self.flush(finished=True)

        # Write the hash and other details to a file.
        hash_str, num_files, num_subdirs = hash_directory(self.log_dir)
        hash_path = os.path.join(self.log_dir, "hash.txt")
        with open(hash_path, "w") as f:
            f.write(hash_str)
            f.write("\n")
            f.write("{} files\n".format(num_files))
            f.write("{} subdirectories\n".format(num_subdirs))

        self.finalized = True

    @staticmethod
    def _decorate_text(text: str, color: str, weight: str = "bold", demarcate: bool = False) -> str:
        """
        Returns a string of text with HTML styling for weight and color.
        """
        if demarcate:
            text = f"<<<<<  {text}  >>>>>"
        return f'<span style="color: {color}; font-weight: {weight};">{text}</span>'

    @staticmethod
    def _link_to_image(image_path: str, description: str) -> str:
        """
        Returns an HTML string defining a thumbnail link to an image.
        """
        # To avoid a bug in heml rendering aht displays underscores to the left of thumbnails,
        # define the following string on a single line.
        link = f"""<a href="{image_path}"><img src="{image_path}" alt="{description}" style="width: 300px; height: auto;"></a>"""
        return link

    def _get_next_page_id(self) -> int:
        """Returns the next page id and increments the counter."""
        self.last_page_id += 1
        return self.last_page_id

    def _create_run_dir(self) -> None:
        """Creates a fresh log directory."""
        if os.path.exists(self.log_dir):
            shutil.rmtree(self.log_dir)
        os.makedirs(self.log_dir)

    def _add_page(self, summary: str, show_in_call_tree: bool = True, finished: bool = True) -> "Page":
        """
        Adds a new page to the log.
        """
        page = Page(
            page_logger=self,
            index=self._get_next_page_id(),
            summary=summary,
            indent_level=len(self.page_stack.stack),
            show_in_call_tree=show_in_call_tree,
            finished=finished,
        )
        self.pages.append(page)
        self.flush()
        if len(self.page_stack.stack) > 0:
            # Insert a link to the new page into the calling page.
            self.info("\n" + page.full_link)
        return page

    def _log_text(self, text: str) -> None:
        """
        Adds text to the current page.
        """
        page = self.page_stack.top()
        if page is not None:
            page.add_lines(text, flush=True)

    def debug(self, line: str) -> None:
        """
        Adds DEBUG text to the current page if debugging level <= DEBUG.
        """
        if self.level <= self.levels["DEBUG"]:
            self._log_text(line)

    def info(self, line: str) -> None:
        """
        Adds INFO text to the current page if debugging level <= INFO.
        """
        if self.level <= self.levels["INFO"]:
            self._log_text(line)

    def warning(self, line: str) -> None:
        """
        Adds WARNING text to the current page if debugging level <= WARNING.
        """
        if self.level <= self.levels["WARNING"]:
            self._log_text(line)

    def error(self, line: str) -> None:
        """
        Adds ERROR text to the current page if debugging level <= ERROR.
        """
        if self.level <= self.levels["ERROR"]:
            self._log_text(line)

    def critical(self, line: str) -> None:
        """
        Adds CRITICAL text to the current page if debugging level <= CRITICAL.
        """
        if self.level <= self.levels["CRITICAL"]:
            self._log_text(line)

    def _message_source(self, message: LLMMessage) -> str:
        """
        Returns a decorated string indicating the source of a message.
        """
        source = "UNKNOWN"
        color = "black"
        if isinstance(message, SystemMessage):
            source = "SYSTEM"
            color = "purple"
        elif isinstance(message, UserMessage):
            source = "USER"
            color = "blue"
        elif isinstance(message, AssistantMessage):
            source = "ASSISTANT"
            color = "green"
        elif isinstance(message, FunctionExecutionResultMessage):
            source = "FUNCTION"
            color = "red"
        return self._decorate_text(source, color, demarcate=True)

    def _format_message_content(self, message_content: MessageContent) -> str:
        """
        Formats the message content for logging.
        """
        # Start by converting the message content to a list of strings.
        content_list: List[str] = []
        content = message_content
        if isinstance(content, str):
            content_list.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    content_list.append(item.rstrip())
                elif isinstance(item, Image):
                    # Save the image to disk.
                    image_filename = str(self._get_next_page_id()) + " image.jpg"
                    image_path = os.path.join(self.log_dir, image_filename)
                    item.image.save(image_path)
                    # Add a link to the image.
                    content_list.append(self._link_to_image(image_filename, "message_image"))
                elif isinstance(item, Dict):
                    # Add a dictionary to the log.
                    json_str = json.dumps(item, indent=4)
                    content_list.append(json_str)
                else:
                    content_list.append(str(item).rstrip())
        else:
            content_list.append("<UNKNOWN MESSAGE CONTENT>")

        # Convert the list of strings to a single string containing newline separators.
        output = ""
        for item in content_list:
            output += f"\n{item}\n"
        return output

    def log_message_content(self, message_content: MessageContent, summary: str) -> None:
        """
        Adds a page containing the message's content, including any images.
        """
        if self.level > self.levels["INFO"]:
            return None
        page = self._add_page(summary=summary, show_in_call_tree=False)
        self.page_stack.write_stack_to_page(page)
        page.add_lines(self._format_message_content(message_content=message_content))
        page.flush()

    def log_dict_list(self, content: List[Mapping[str, Any]], summary: str) -> None:
        """
        Adds a page containing a list of dicts.
        """
        if self.level > self.levels["INFO"]:
            return None
        page = self._add_page(summary=summary, show_in_call_tree=False)
        self.page_stack.write_stack_to_page(page)

        for item in content:
            json_str = json.dumps(item, indent=4)
            page.add_lines(json_str)

        page.flush()

    def _log_model_messages(
        self, summary: str, input_messages: List[LLMMessage], response_str: str, usage: RequestUsage | None
    ) -> Optional["Page"]:
        """
        Adds a page containing the messages to a model (including any input images) and its response.
        """
        page = self._add_page(summary=summary, show_in_call_tree=False)
        self.page_stack.write_stack_to_page(page)

        if usage is not None:
            page.add_lines("{} prompt tokens".format(usage.prompt_tokens))
            page.add_lines("{} completion tokens".format(usage.completion_tokens))
        for m in input_messages:
            page.add_lines("\n" + self._message_source(m))
            page.add_lines(self._format_message_content(message_content=m.content))
        page.add_lines("\n" + self._decorate_text("ASSISTANT RESPONSE", "green", demarcate=True))
        page.add_lines("\n" + response_str + "\n")
        page.flush()
        return page

    def log_model_call(
        self, summary: str, input_messages: List[LLMMessage], response: CreateResult
    ) -> Optional["Page"]:
        """
        Logs messages sent to a model and the TaskResult response to a new page.
        """
        if self.level > self.levels["INFO"]:
            return None

        response_str = response.content
        if not isinstance(response_str, str):
            response_str = "??"

        page = self._log_model_messages(summary, input_messages, response_str, response.usage)
        return page

    def log_model_task(
        self, summary: str, input_messages: List[LLMMessage], task_result: TaskResult
    ) -> Optional["Page"]:
        """
        Logs messages sent to a model and the TaskResult response to a new page.
        """
        if self.level > self.levels["INFO"]:
            return None

        messages: Sequence[AgentEvent | ChatMessage] = task_result.messages
        message = messages[-1]
        response_str = message.content
        if not isinstance(response_str, str):
            response_str = "??"

        if hasattr(message, "models_usage"):
            usage: RequestUsage | None = message.models_usage
        else:
            usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

        page = self._log_model_messages(summary, input_messages, response_str, usage)
        return page

    def log_link_to_local_file(self, file_path: str) -> str:
        """
        Returns a link to a local file in the log.
        """
        file_name = os.path.basename(file_path)
        link = f'<a href="{file_name}">{file_name}</a>'
        return link

    def add_link_to_image(self, description: str, source_image_path: str) -> None:
        """
        Inserts a thumbnail link to an image to the page.
        """
        # Remove every character from the string 'description' that is not alphanumeric or a space.
        description = "".join(e for e in description if e.isalnum() or e.isspace())
        target_image_filename = str(self._get_next_page_id()) + " - " + description
        # Copy the image to the log directory.
        local_image_path = os.path.join(self.log_dir, target_image_filename)
        shutil.copyfile(source_image_path, local_image_path)
        self._log_text("\n" + description)
        self._log_text(self._link_to_image(target_image_filename, description))

    def flush(self, finished: bool = False) -> None:
        """
        Writes the current state of the log to disk.
        """
        if self.level > self.levels["INFO"]:
            return
        # Create a call tree of the log.
        call_tree_path = os.path.join(self.log_dir, self.name + ".html")
        with open(call_tree_path, "w") as f:
            f.write(_html_opening("0 Call Tree", finished=finished))
            f.write(f"<h3>{self.name}</h3>")
            f.write("\n")
            for page in self.pages:
                if page.show_in_call_tree:
                    f.write(page.line_text + "\n")
            f.write("\n")
            f.write(_html_closing())

    def enter_function(self) -> Optional["Page"]:
        """
        Adds a new page corresponding to the current function call.
        """
        if self.level > self.levels["INFO"]:
            return None

        page = None
        frame_type = inspect.currentframe()
        if frame_type is not None:
            frame = frame_type.f_back  # Get the calling frame
            if frame is not None:
                # Check if it's a method by looking for 'self' or 'cls' in f_locals
                if "self" in frame.f_locals:
                    class_name = type(frame.f_locals["self"]).__name__
                elif "cls" in frame.f_locals:
                    class_name = frame.f_locals["cls"].__name__
                else:
                    class_name = None  # Not part of a class

                if class_name is None:  # Not part of a class
                    caller_name = frame.f_code.co_name
                else:
                    caller_name = class_name + "." + frame.f_code.co_name

                # Create a new page for this function.
                page = self._add_page(summary=caller_name, show_in_call_tree=True, finished=False)
                self.page_stack.push(page)
                self.page_stack.write_stack_to_page(page)

                page.add_lines("\nENTER {}".format(caller_name), flush=True)
        return page

    def leave_function(self) -> None:
        """
        Finishes the page corresponding to the current function call.
        """
        if self.level > self.levels["INFO"]:
            return None
        page = self.page_stack.top()
        if page is not None:
            page.finished = True
            page.add_lines("\nLEAVE {}".format(page.summary), flush=True)
            self.page_stack.pop()


class Page:
    """
    Represents a single HTML page in the logger output.

    Args:
        page_logger: The PageLogger object that created this page.
        index: The index of the page.
        summary: A brief summary of the page's contents for display.
        indent_level: The level of indentation in the call tree.
        show_in_call_tree: Whether to display the page in the call tree.
        finished: Whether the page is complete.
    """

    def __init__(
        self,
        page_logger: PageLogger,
        index: int,
        summary: str,
        indent_level: int,
        show_in_call_tree: bool = True,
        finished: bool = True,
    ):
        """
        Initializes and writes to a new HTML page.
        """
        self.page_logger = page_logger
        self.index_str = str(index)
        self.summary = summary
        self.indent_level = indent_level
        self.show_in_call_tree = show_in_call_tree
        self.finished = finished
        self.file_title = self.index_str + "  " + self.summary
        self.indentation_text = "|&emsp;" * self.indent_level
        self.full_link = f'<a href="{self.index_str}.html">{self.file_title}</a>'
        self.line_text = self.indentation_text + self.full_link
        self.lines: List[str] = []
        self.flush()

    def add_lines(self, lines: str, flush: bool = False) -> None:
        """
        Adds one or more lines to the page.
        """
        lines_to_add: List[str] = []
        if "\n" in lines:
            lines_to_add = lines.split("\n")
        else:
            lines_to_add.append(lines)
        self.lines.extend(lines_to_add)
        if flush:
            self.flush()

    def flush(self) -> None:
        """
        Writes the HTML page to disk.
        """
        page_path = os.path.join(self.page_logger.log_dir, self.index_str + ".html")
        with open(page_path, "w") as f:
            f.write(_html_opening(self.file_title, finished=self.finished))
            f.write(f"<h3>{self.file_title}</h3>\n")
            for line in self.lines:
                try:
                    f.write(f"{line}\n")
                except UnicodeEncodeError:
                    f.write("UnicodeEncodeError in this line.\n")
            f.write(_html_closing())
            f.flush()


class PageStack:
    """
    A call stack containing a list of currently active function pages in the order they called each other.
    """

    def __init__(self) -> None:
        self.stack: List[Page] = []

    def push(self, page: Page) -> None:
        """Adds a page to the top of the stack."""
        self.stack.append(page)

    def pop(self) -> Page:
        """Removes and returns the top page from the stack"""
        return self.stack.pop()

    def size(self) -> int:
        """Returns the number of pages in the stack."""
        return len(self.stack)

    def top(self) -> Page | None:
        """Returns the top page from the stack without removing it"""
        if self.size() == 0:
            return None
        return self.stack[-1]

    def write_stack_to_page(self, page: Page) -> None:
        # Logs a properly indented string displaying the current call stack.
        page.add_lines("\nCALL STACK")
        for stack_page in self.stack:
            page.add_lines(stack_page.line_text)
        page.add_lines("")
        page.add_lines("")
        page.flush()
