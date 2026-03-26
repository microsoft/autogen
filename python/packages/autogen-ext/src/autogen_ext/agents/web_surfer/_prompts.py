import re


def _sanitize_page_metadata(value: str, max_length: int = 200) -> str:
    """Sanitize webpage metadata (title, URL) before embedding in prompts.

    This prevents indirect prompt injection via attacker-controlled page
    metadata such as the HTML <title> tag. The function:
    - Strips control characters and collapses whitespace
    - Truncates to a safe length to limit prompt space consumption
    - Removes markdown link syntax that could confuse the LLM
    """
    # Remove control characters (newlines, tabs, null bytes, etc.)
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", value)
    # Collapse multiple spaces
    sanitized = re.sub(r" {2,}", " ", sanitized).strip()
    # Remove markdown link syntax characters that could break prompt structure
    sanitized = re.sub(r"[\[\]\(\)]", "", sanitized)
    # Truncate to prevent excessive prompt space consumption
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


WEB_SURFER_TOOL_PROMPT_MM = """
{state_description}

Consider the following screenshot of the page. In this screenshot, interactive elements are outlined in bounding boxes of different colors. Each bounding box has a numeric ID label in the same color. Additional information about each visible label is listed below:

{visible_targets}{other_targets_str}{focused_hint}

You are to respond to my next request by selecting an appropriate tool from the following set, or by answering the question directly if possible:

{tool_names}

When deciding between tools, consider if the request can be best addressed by:
    - the contents of the CURRENT VIEWPORT (in which case actions like clicking links, clicking buttons, inputting text, or hovering over an element, might be more appropriate)
    - contents found elsewhere on the CURRENT WEBPAGE <page_title>{title}</page_title> (<page_url>{url}</page_url>), in which case actions like scrolling, summarization, or full-page Q&A might be most appropriate
    - on ANOTHER WEBSITE entirely (in which case actions like performing a new web search might be the best option)

My request follows:
"""

WEB_SURFER_TOOL_PROMPT_TEXT = """
{state_description}

You have also identified the following interactive components:

{visible_targets}{other_targets_str}{focused_hint}

You are to respond to my next request by selecting an appropriate tool from the following set, or by answering the question directly if possible:

{tool_names}

When deciding between tools, consider if the request can be best addressed by:
    - the contents of the CURRENT VIEWPORT (in which case actions like clicking links, clicking buttons, inputting text, or hovering over an element, might be more appropriate)
    - contents found elsewhere on the CURRENT WEBPAGE <page_title>{title}</page_title> (<page_url>{url}</page_url>), in which case actions like scrolling, summarization, or full-page Q&A might be most appropriate
    - on ANOTHER WEBSITE entirely (in which case actions like performing a new web search might be the best option)

My request follows:
"""


WEB_SURFER_QA_SYSTEM_MESSAGE = """
You are a helpful assistant that can summarize long documents to answer question.
"""


def WEB_SURFER_QA_PROMPT(title: str, question: str | None = None) -> str:
    sanitized_title = _sanitize_page_metadata(title)
    base_prompt = f"We are visiting the webpage <page_title>{sanitized_title}</page_title>. Its full-text content are pasted below, along with a screenshot of the page's current viewport."
    if question is not None:
        return (
            f"{base_prompt} Please summarize the webpage into one or two paragraphs with respect to '{question}':\n\n"
        )
    else:
        return f"{base_prompt} Please summarize the webpage into one or two paragraphs:\n\n"
