import inspect
import json
import os
import shutil
import time
from typing import Dict, List, Union

from autogen_core import FunctionCall, Image
from autogen_core.models import (
    AssistantMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from ._utils import MessageContent


def html_opening(file_title: str, finished: bool = False) -> str:
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


def html_closing() -> str:
    """
    Return the closing text of a simple HTML file.
    """
    return """</body></html>"""


class PageLogger:
    """
    Logs text and images to a set of HTML pages, one per function/method, linked to each other in a call tree.

    Args:
        settings: A dictionary containing the following keys:
            - enabled: A boolean indicating whether logging is enabled.

    Methods:
        info: Adds text to the current page.
        error: Adds text to the current page.
        log_message_content: Adds a page containing the message's content, including any images.
        log_model_call: Adds a page containing all messages to or from a model, including any images.
        log_link_to_local_file: Returns a link to a local file in the log.
        flush: Writes the current state of the log to disk.
        enter_function: Adds a new page corresponding to the current function call.
        leave_function: Finishes the page corresponding to the current function
    """

    def __init__(self, settings: Dict):
        self.enabled = settings["enabled"]
        if not self.enabled:
            return
        self.log_dir = os.path.expanduser(settings["path"])
        self.page_stack = PageStack()
        self.pages = []
        self.last_page_id = 0
        self.name = "0  Call Tree"
        self._create_run_dir()
        self.flush()

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

    def info(self, line: str) -> None:
        """
        Adds text to the current page.
        """
        if not self.enabled:
            return
        page = self.page_stack.top()
        page.add_lines(line, flush=True)

    def error(self, line: str) -> None:
        """
        Adds text to the current page.
        """
        if not self.enabled:
            return
        page = self.page_stack.top()
        page.add_lines(line, flush=True)

    def _message_source(self, message: LLMMessage) -> str:
        """
        Returns a string indicating the source of a message.
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

    def _decorate_text(self, text: str, color: str, weight: str = "bold", demarcate: bool = False) -> str:
        """
        Returns a string of text with HTML styling for weight and color.
        """
        if demarcate:
            text = f"<<<<<  {text}  >>>>>"
        return f'<span style="color: {color}; font-weight: {weight};">{text}</span>'

    def _format_message_content(
        self, page: "Page", message: LLMMessage | None = None, message_content: MessageContent | None = None
    ) -> str:
        """
        Formats the message content for logging. Either message or message_content must not be None.
        """
        # Start by converting the message content to a list of strings.
        content = None
        content_list = []
        if message_content is not None:
            content = message_content
        if message is not None:
            content = message.content
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
                    content_list.append(page.link_to_image(image_filename, "message_image"))
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
        page = self._add_page(summary=summary, show_in_call_tree=False)
        self.page_stack.write_stack_to_page(page)
        page.add_lines(self._format_message_content(page, message_content=message_content))
        page.flush()

    def log_model_call(self, summary: str, input_messages: List[LLMMessage], response: LLMMessage) -> "Page":
        """
        Adds a page containing all messages to or from a model, including any images.
        """
        if not self.enabled:
            return None
        page = self._add_page(summary=summary, show_in_call_tree=False)
        self.page_stack.write_stack_to_page(page)
        page.add_lines("{} prompt tokens".format(response.usage.prompt_tokens))
        page.add_lines("{} completion tokens".format(response.usage.completion_tokens))
        for m in input_messages:
            page.add_lines("\n" + self._message_source(m))
            page.add_lines(self._format_message_content(page, message=m))
        page.add_lines("\n" + self._decorate_text("ASSISTANT RESPONSE", "green", demarcate=True))
        page.add_lines(self._format_message_content(page, message=response))
        page.flush()
        return page

    def log_link_to_local_file(self, file_path: str) -> str:
        """
        Returns a link to a local file in the log.
        """
        file_name = os.path.basename(file_path)
        link = f'<a href="{file_name}">{file_name}</a>'
        return link

    def flush(self, finished: bool = False) -> None:
        """
        Writes the current state of the log to disk.
        """
        if not self.enabled:
            return
        # Create a call tree of the log.
        call_tree_path = os.path.join(self.log_dir, self.name + ".html")
        with open(call_tree_path, "w") as f:
            f.write(html_opening("0 Call Tree", finished=finished))
            f.write(f"<h3>{self.name}</h3>")
            f.write("\n")
            for page in self.pages:
                if page.show_in_call_tree:
                    f.write(page.line_text + "\n")
            f.write("\n")
            f.write(html_closing())
        time.sleep(0.1)  # Avoids race conditions when writing multiple files in quick succession.

    def enter_function(self) -> "Page":
        """
        Adds a new page corresponding to the current function call.
        """
        if not self.enabled:
            return None
        frame = inspect.currentframe().f_back  # Get the calling frame

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
        if not self.enabled:
            return
        page = self.page_stack.top()
        page.finished = True
        page.add_lines("\nLEAVE {}".format(page.summary), flush=True)
        self.page_stack.pop()


class Page:
    """
    Represents a single HTML page in the logger output.
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
        self.indentation_text = "|&emsp;"*self.indent_level
        self.full_link = f'<a href="{self.index_str}.html">{self.file_title}</a>'
        self.line_text = self.indentation_text + self.full_link
        self.lines = []
        self.flush()

    def add_lines(self, lines: str, flush: bool = False) -> None:
        """
        Adds one or more lines to the page.
        """
        lines_to_add = []
        if "\n" in lines:
            lines_to_add = lines.split("\n")
        else:
            lines_to_add.append(lines)
        self.lines.extend(lines_to_add)
        if flush:
            self.flush()

    def link_to_image(self, image_path: str, description: str) -> str:
        """
        Returns an HTML string defining a thumbnail link to an image.
        """
        # To avoid a bug in heml rendering aht displays underscores to the left of thumbnails,
        # define the following string on a single line.
        link = f"""<a href="{image_path}"><img src="{image_path}" alt="{description}" style="width: 300px; height: auto;"></a>"""
        return link

    def add_link_to_image(self, description: str, source_image_path: str) -> None:
        """
        Inserts a thumbnail link to an image to the page.
        """
        # Remove every character from the string 'description' that is not alphanumeric or a space.
        description = "".join(e for e in description if e.isalnum() or e.isspace())
        target_image_filename = str(self.page_logger._get_next_page_id()) + " - " + description
        # Copy the image to the log directory.
        local_image_path = os.path.join(self.page_logger.log_dir, target_image_filename)
        shutil.copyfile(source_image_path, local_image_path)
        self.add_lines("\n" + description)
        self.add_lines(self.link_to_image(target_image_filename, description), flush=True)

    def flush(self) -> None:
        """
        Writes the HTML page to disk.
        """
        page_path = os.path.join(self.page_logger.log_dir, self.index_str + ".html")
        with open(page_path, "w") as f:
            f.write(html_opening(self.file_title, finished=self.finished))
            f.write(f"<h3>{self.file_title}</h3>\n")
            for line in self.lines:
                try:
                    f.write(f"{line}\n")
                except UnicodeEncodeError:
                    f.write("UnicodeEncodeError in this line.\n")
            f.write(html_closing())
            f.flush()
        time.sleep(0.1)  # Avoids race conditions when writing multiple files in quick succession.


class PageStack:
    """
    A call stack containing a list of currently active function pages in the order they called each other.
    """

    def __init__(self):
        self.stack = []

    def push(self, page: Page) -> None:
        """Adds a page to the top of the stack."""
        self.stack.append(page)

    def pop(self) -> Page:
        """Removes and returns the top page from the stack"""
        return self.stack.pop()

    def top(self) -> Page:
        """Returns the top page from the stack without removing it"""
        return self.stack[-1]

    def write_stack_to_page(self, page: Page) -> None:
        # Logs a properly indented string displaying the current call stack.
        page.add_lines("\nCALL STACK")
        for stack_page in self.stack:
            page.add_lines(stack_page.line_text)
        page.add_lines("")
        page.add_lines("")
        page.flush()
