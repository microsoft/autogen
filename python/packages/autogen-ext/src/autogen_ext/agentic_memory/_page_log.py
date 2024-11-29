import os
import shutil
import time
from typing import List

from autogen_core.components import Image
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    FunctionExecutionResultMessage,
)


class Page:
    def __init__(self, page_log, index, summary, details, method_call, indent_level, show_in_overview=True, final=True):
        self.page_log = page_log
        self.index_str = str(index)
        self.link_text = None
        self.full_link = None
        self.file_title = None
        self.unindented_line_text = None
        self.line_text = None
        self.indentation_text = None
        self.summary = summary
        self.details = details
        self.method_call = method_call
        self.indent_level = indent_level
        self.show_in_overview = show_in_overview
        self.final = final
        self.compose_line(details)
        self.lines = []
        self.flush()

    def compose_line(self, details, flush=False):
        self.details = details
        self.link_text = self.index_str + '  ' + self.summary
        self.indentation_text = ""
        for i in range(self.indent_level):
            self.indentation_text += "|&emsp;"
        self.file_title = self.link_text + ' ' + self.details
        self.full_link = self.link_to_page_file()
        self.unindented_line_text = self.full_link + ' ' + self.details
        self.line_text = self.indentation_text + self.unindented_line_text
        if flush:
            self.flush()

    def update_details(self, details):
        self.compose_line(details, flush=True)
        self.page_log.flush()

    def link_to_page_file(self):
        return f'<a href="{self.index_str}.html">{self.link_text}</a>'

    def add_lines(self, line, flush=False):
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
        target_image_filename = (str(self.page_log.get_next_page_id()) + ' - ' + description)
        local_image_path = os.path.join(self.page_log.run_dir_path, target_image_filename)
        shutil.copyfile(source_image_path, local_image_path)
        self.add_lines('\n' + description)
        self.add_lines(self.link_to_image(target_image_filename, description), flush=True)

    def delete_last_line(self):
        if len(self.lines) > 0:
            self.lines.pop()

    def flush(self):
        page_path = os.path.join(self.page_log.run_dir_path, self.index_str + ".html")
        with open(page_path, "w") as f:
            f.write(self.page_log.html_opening(self.file_title, final=self.final))
            f.write(f"<h3>{self.file_title}</h3>\n")
            for line in self.lines:
                # Call f.write in a try block to catch any UnicodeEncodeErrors.
                try:
                    f.write(f"{line}\n")
                except UnicodeEncodeError:
                    f.write(f"UnicodeEncodeError in this line.\n")
            f.write(self.page_log.html_closing())
            f.flush()
        time.sleep(0.1)


class PageLog:
    def __init__(self, path, run_id):
        self.log_dir = os.path.expanduser(path)
        self.run_id = run_id
        self.page_stack = PageStack()
        self.pages = []
        self.last_page_id = 0
        self.entry_lines = []
        self.exit_lines = []
        self.run_dir_path = None
        self.name = "0 Overview"
        self.create_run_dir()
        self.token_counts_path = self.create_token_counts_file()
        self.flush()

    def get_next_page_id(self):
        self.last_page_id += 1
        return self.last_page_id

    def create_run_dir(self):
        # Create a fresh run directory.
        self.run_dir_path = os.path.join(self.log_dir, f"{self.run_id}")
        if os.path.exists(self.run_dir_path):
            shutil.rmtree(self.run_dir_path)
        os.makedirs(self.run_dir_path)

    def create_token_counts_file(self):
        token_counts_path = os.path.join(self.run_dir_path, "token_counts.csv")
        f = open(token_counts_path, "w")
        f.close()  # The file starts empty and will be appended to later.
        return token_counts_path

    def write_token_count(self, num_input_tokens, caller, details_path=None):
        # Write the number of input tokens to the file, with caller and path to other details.
        with open(self.token_counts_path, "a") as f:
            f.write(f"{num_input_tokens},{caller},{details_path}\n")

    def num_subdirectories(self):
        # Return the number of subdirectories in the log directory.
        return len([name for name in os.listdir(self.log_dir) if os.path.isdir(os.path.join(self.log_dir, name))])

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

    def add_page(self, summary, details, method_call=None, show_in_overview=True, final=True):
        # Add a page to the log.
        page = Page(page_log=self,
                    index=self.get_next_page_id(),
                    summary=summary,
                    details=details,
                    method_call=method_call,
                    indent_level=len(self.page_stack.stack),
                    show_in_overview=show_in_overview,
                    final=final)
        self.pages.append(page)
        self.flush()

        if len(self.page_stack.stack) > 0:
            # Insert a link to the new page into the calling page.
            self.page_stack.stack[-1].add_lines(page.unindented_line_text, flush=True)

        return page

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
                    image_path = os.path.join(self.run_dir_path, image_filename)
                    item.image.save(image_path)
                    # Add a link to the image.
                    content_list.append(page.link_to_image(image_filename, "message_image"))
                else:
                    content_list.append(str(item).rstrip())
        else:
            content_list.append("<UNKNOWN MESSAGE CONTENT>")

        # Convert the list of strings to a single string with newline separators.
        output = ""
        for item in content_list:
            output += f"\n{item}\n"
        return output

    def add_message_content(self, message_content, summary, details=""):
        # Add a page containing a message's content.
        page = self.add_page(summary=summary,
                             details=details,
                             show_in_overview=False)
        self.page_stack.write_stack_to_page(page)
        page.add_lines(self.message_content(page, message_content=message_content))
        page.flush()

    def add_broadcast_message(self, message, operation):
        # Add a page containing a message being broadcast.
        page = self.add_page(summary="Broadcast Message",
                             details=operation,
                             method_call="broadcast message",
                             show_in_overview=False)
        self.page_stack.write_stack_to_page(page)
        page.add_lines(self.message_source(message))
        page.add_lines(self.message_content(page, message=message))
        page.flush()

    def add_model_call(self, description, details, input_messages, response,
                       tools=None, json_output=None, extra_create_args=None,
                       num_input_tokens=None, caller=None):
        # Add a model call to the log.
        page = self.add_page(summary=description,
                             details=details,
                             method_call="model call",
                             show_in_overview=False)
        self.page_stack.write_stack_to_page(page)
        for i, m in enumerate(input_messages):
            page.add_lines('\n' + self.message_source(m))
            page.add_lines(self.message_content(page, message=m))
        page.add_lines("\n" + self.decorate_text("ASSISTANT RESPONSE", "green", demarcate=True))
        if response is None:
            page.add_lines("\n  TOO MANY INPUT TOKENS, NO RESPONSE GENERATED")
        else:
            page.add_lines(self.message_content(page, message=response))
        page.flush()
        if num_input_tokens is not None and caller is not None:
            # Add a line to the token count file.
            self.write_token_count(num_input_tokens, caller, page.index_str + ".html")
        return page

    def prepend_entry_line(self, line):
        self.entry_lines.insert(0, line)

    def append_entry_line(self, line):
        self.entry_lines.append(line)

    def prepend_exit_line(self, line):
        self.exit_lines.insert(0, line)
        
    def append_exit_line(self, line):
        self.exit_lines.append(line)

    def link_to_local_file(self, file_path):
        file_name = os.path.basename(file_path)
        link = f'<a href="{file_name}">{file_name}</a>'
        return link

    def last_page(self):
        if len(self.page_stack.stack) > 0:
            return self.page_stack.stack[-1]
        else:
            return None

    def flush(self, final=False):
        # Create an overview of the log.
        overview_path = os.path.join(self.run_dir_path, self.name + ".html")
        with open(overview_path, "w") as f:
            f.write(self.html_opening("0 Overview", final=final))
            f.write(f"<h3>{self.name}</h3>\n")
            for line in self.entry_lines:
                f.write(line + "\n")
            f.write("\n")
            for page in self.pages:
                if page.show_in_overview:
                    f.write(page.line_text + "\n")
            f.write("\n")
            for line in self.exit_lines:
                f.write(line + "\n")
            f.write(self.html_closing())
        time.sleep(0.1)

    def begin_page(self, summary, details, method_call, show_in_overview=True):
        # Perform a set of logging actions that are often performed at the beginning of a caller's method.
        page = self.add_page(
            summary=summary,
            details=details,
            method_call=method_call,
            show_in_overview=show_in_overview,
            final=False)

        self.page_stack.push(page)
        self.page_stack.write_stack_to_page(page)

        page.add_lines("\nENTER {}".format(method_call), flush=True)
        return page

    def finish_page(self, page):
        # Perform a set of logging actions that are often performed at the end of a caller's method.
        page.final = True
        page.add_lines("LEAVE {}".format(page.method_call), flush=True)
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
        page.add_lines("\nCALL STACK")
        for stack_page in self.stack:
            page.add_lines(stack_page.line_text)
        page.add_lines("")
        page.add_lines("")
        page.flush()
