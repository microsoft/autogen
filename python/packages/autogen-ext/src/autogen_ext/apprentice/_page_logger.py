import os
import shutil
import time
import json
import inspect
from typing import List, Dict

from autogen_core import Image
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    FunctionExecutionResultMessage,
)


class Page:
    def __init__(self, page_logger, index, summary, indent_level, show_in_overview=True, final=True):
        self.page_logger = page_logger
        self.index_str = str(index)
        self.summary = summary
        self.indent_level = indent_level
        self.show_in_overview = show_in_overview
        self.final = final
        self.file_title = self.index_str + '  ' + self.summary
        self.indentation_text = ""
        for i in range(self.indent_level):
            self.indentation_text += "|&emsp;"
        self.full_link = self.link_to_page_file()
        self.line_text = self.indentation_text + self.full_link
        self.lines = []
        self.flush()

    def link_to_page_file(self):
        return f'<a href="{self.index_str}.html">{self.file_title}</a>'

    def _add_lines(self, line, flush=False):
        # If the string 'line' consists of multiple lines, separate them into a list.
        lines_to_add = []
        if "\n" in line:
            lines_to_add = line.split("\n")
        else:
            lines_to_add.append(line)

        self.lines.extend(lines_to_add)

        if flush:
            self.flush()

    def link_to_image(self, image_path, description):
        # Add a thumbnail that links to the image.
        # If the following html string is indented, underscores appear to the left of thumbnails.
        link = f"""<a href="{image_path}"><img src="{image_path}" alt="{description}" style="width: 300px; height: auto;"></a>"""
        return link

    def add_link_to_image(self, description, source_image_path):
        # Copy the image to the run directory.
        # Remove every character from the string 'description' that is not alphanumeric or a space.
        description = ''.join(e for e in description if e.isalnum() or e.isspace())
        target_image_filename = (str(self.page_logger.get_next_page_id()) + ' - ' + description)
        local_image_path = os.path.join(self.page_logger.log_dir, target_image_filename)
        shutil.copyfile(source_image_path, local_image_path)
        self._add_lines('\n' + description)
        self._add_lines(self.link_to_image(target_image_filename, description), flush=True)

    def flush(self):
        page_path = os.path.join(self.page_logger.log_dir, self.index_str + ".html")
        with open(page_path, "w") as f:
            f.write(self.page_logger.html_opening(self.file_title, final=self.final))
            f.write(f"<h3>{self.file_title}</h3>\n")
            for line in self.lines:
                # Call f.write in a try block to catch any UnicodeEncodeErrors.
                try:
                    f.write(f"{line}\n")
                except UnicodeEncodeError:
                    f.write(f"UnicodeEncodeError in this line.\n")
            f.write(self.page_logger.html_closing())
            f.flush()
        time.sleep(0.1)


class PageLogger:
    def __init__(self, settings):
        self.enabled = settings["enabled"]
        if not self.enabled:
            return
        self.log_dir = os.path.expanduser(settings["path"])
        self.page_stack = PageStack()
        self.pages = []
        self.last_page_id = 0
        self.name = "0 Overview"
        self.create_run_dir()
        self.flush()

    def get_next_page_id(self):
        self.last_page_id += 1
        return self.last_page_id

    def create_run_dir(self):
        # Create a fresh log directory.
        if os.path.exists(self.log_dir):
            shutil.rmtree(self.log_dir)
        os.makedirs(self.log_dir)

    def html_opening(self, file_title, final=False):
        # Return the opening text of a simple HTML file.
        refresh_tag = '<meta http-equiv="refresh" content="2">' if not final else ""
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

    def html_closing(self):
        # Return the closing text of a simple HTML file.
        return """</body></html>"""

    def add_page(self, summary, show_in_overview=True, final=True):
        # Add a page to the log.
        page = Page(page_logger=self,
                    index=self.get_next_page_id(),
                    summary=summary,
                    indent_level=len(self.page_stack.stack),
                    show_in_overview=show_in_overview,
                    final=final)
        self.pages.append(page)
        self.flush()

        if len(self.page_stack.stack) > 0:
            # Insert a link to the new page into the calling page.
            self._add_lines('\n' + page.full_link, flush=True)

        return page

    def _add_lines(self, line, flush=False):
        # Add lines to the current page (at the top of the page stack).
        page = self.page_stack.top()
        page._add_lines(line, flush=flush)

    def info(self, line):
        if not self.enabled:
            return
        # Add lines to the current page (at the top of the page stack).
        page = self.page_stack.top()
        page._add_lines(line, flush=True)

    def error(self, line):
        if not self.enabled:
            return
        # Add lines to the current page (at the top of the page stack).
        page = self.page_stack.top()
        page._add_lines(line, flush=True)

    def message_source(self, message):
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
        return self.decorate_text(source, color, demarcate=True)

    def decorate_text(self, text, color, weight="bold", demarcate=False):
        if demarcate:
            text = f"<<<<<  {text}  >>>>>"
        return f'<span style="color: {color}; font-weight: {weight};">{text}</span>'

    def message_content(self, page, message=None, message_content=None):
        # Format the message content for logging. Either message or message_content must not be None.
        # Start by converting the message content to a list of strings.
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
                    image_filename = str(self.get_next_page_id()) + " image.jpg"
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

        # Convert the list of strings to a single string with newline separators.
        output = ""
        for item in content_list:
            output += f"\n{item}\n"
        return output

    def add_message_content(self, message_content, summary):
        # Add a page containing a message's content.
        page = self.add_page(summary=summary, show_in_overview=False)
        self.page_stack.write_stack_to_page(page)
        page._add_lines(self.message_content(page, message_content=message_content))
        page.flush()

    def add_model_call(self, summary, input_messages, response):
        if not self.enabled:
            return
        # Add a model call to the log.
        page = self.add_page(summary=summary, show_in_overview=False)
        self.page_stack.write_stack_to_page(page)
        page._add_lines("{} prompt tokens".format(response.usage.prompt_tokens))
        page._add_lines("{} completion tokens".format(response.usage.completion_tokens))
        for i, m in enumerate(input_messages):
            page._add_lines('\n' + self.message_source(m))
            page._add_lines(self.message_content(page, message=m))
        page._add_lines("\n" + self.decorate_text("ASSISTANT RESPONSE", "green", demarcate=True))
        page._add_lines(self.message_content(page, message=response))
        page.flush()
        return page

    def link_to_local_file(self, file_path):
        file_name = os.path.basename(file_path)
        link = f'<a href="{file_name}">{file_name}</a>'
        return link

    def flush(self, final=False):
        if not self.enabled:
            return
        # Create an overview of the log.
        overview_path = os.path.join(self.log_dir, self.name + ".html")
        with open(overview_path, "w") as f:
            f.write(self.html_opening("0 Overview", final=final))
            f.write(f"<h3>{self.name}</h3>")
            f.write("\n")
            for page in self.pages:
                if page.show_in_overview:
                    f.write(page.line_text + "\n")
            f.write("\n")
            f.write(self.html_closing())
        time.sleep(0.1)

    def enter_function(self):
        # Perform a set of logging actions that are often performed at the beginning of a caller's method.
        if not self.enabled:
            return
        frame = inspect.currentframe().f_back  # Get the calling frame

        # Check if it's a method by looking for 'self' or 'cls' in f_locals
        if 'self' in frame.f_locals:
            class_name = type(frame.f_locals['self']).__name__
        elif 'cls' in frame.f_locals:
            class_name = frame.f_locals['cls'].__name__
        else:
            class_name = None  # Not part of a class

        if class_name is None:  # Not part of a class
            caller_name = frame.f_code.co_name
        else:
            caller_name = class_name + '.' + frame.f_code.co_name

        # Create a new page for this function.
        page = self.add_page(summary=caller_name, show_in_overview=True, final=False)
        self.page_stack.push(page)
        self.page_stack.write_stack_to_page(page)

        page._add_lines("\nENTER {}".format(caller_name), flush=True)
        return page

    def leave_function(self):
        if not self.enabled:
            return
        # Perform a set of logging actions that are often performed at the end of a caller's method.
        page = self.page_stack.top()
        page.final = True
        page._add_lines("\nLEAVE {}".format(page.summary), flush=True)
        self.page_stack.pop()


class PageStack:
    """
    A call stack containing a list of currently active tasks and policies in the order they called each other.
    """
    def __init__(self):
        self.stack = []

    def push(self, page):
        self.stack.append(page)

    def pop(self):
        return self.stack.pop()

    def top(self):
        return self.stack[-1]

    def write_stack_to_page(self, page):
        # Log a properly indented string showing the current state of the call stack.
        page._add_lines("\nCALL STACK")
        for stack_page in self.stack:
            page._add_lines(stack_page.line_text)
        page._add_lines("")
        page._add_lines("")
        page.flush()
