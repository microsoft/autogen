import re

from rich.panel import Panel
from rich.markdown import Markdown
from rich.console import Console


def replace_newlines(text):
    # Match any \n not preceded by 2 spaces, |, or another \n, and not followed by another \n
    pattern = re.compile(r"(?<! {2})(?<!\|)(?<!\n)\n(?!\n)")

    # Replace with "  \n"
    modified_text = pattern.sub("  \n", text)

    return modified_text


def separate_text_code_blocks(s):
    code_block_pattern = r"(```(\w+)?[\s\S]*?```)"
    content_list = []
    code_blocks = re.finditer(code_block_pattern, s)

    last_end = 0
    for match in code_blocks:
        start, end = match.span()
        text_content = s[last_end:start]
        content_list.append((False, text_content))

        code_content = match.group(1)
        language = match.group(2) if match.group(2) else "unknown"

        if language == "markdown":
            content_list.append((False, code_content[11:-3]))
        else:
            content_list.append((language, code_content))

        last_end = end

    if last_end < len(s):
        content_list.append((False, s[last_end:]))

    return content_list


def print_mixed_panel(content, title, align, color, enable_complex=True):
    console = Console()
    panel_content = Markdown(content)
    # print(content)
    # print(repr(content))

    if enable_complex:
        content_list = separate_text_code_blocks(content)

        md_content = f"## {title}  \n"
        for c in content_list:
            md = c[1]
            is_md = c[0]
            if is_md is False:
                md = replace_newlines(md)
            md_content += md

        panel_content = Markdown(md_content)

    mixed_panel = Panel(
        panel_content,
        title=title,
        title_align=align,
        # border_style=f"white on {color}",
        border_style=color,
        padding=(2, 5),
        width=100,
    )

    console.print(mixed_panel)
    console.print("\n" * 4)


def custom_printer(message, sender):
    color = "black on #D1FFBD" if sender.name == "user_proxy" else "white on black"
    align = "right" if sender.name == "user_proxy" else "left"
    print_mixed_panel(message["content"], sender.name, align, color)


def print_messages(recipient, messages, sender, config):
    callback = config["callback"]
    if callback is not None:
        callback(sender, recipient, messages[-1])
    return False, None
