WEB_SURFER_TOOL_PROMPT = """
Consider the following screenshot of a web browser, which is open to the page '{url}'. In this screenshot, interactive elements are outlined in bounding boxes of different colors. Each bounding box has a numeric ID label in the same color. Additional information about each visible label is listed below:

{visible_targets}{other_targets_str}{focused_hint}

You are to respond to the most recent request by selecting an appropriate tool from the following set, or by answering the question directly if possible without tools:

{tool_names}

When deciding between tools, consider if the request can be best addressed by:
    - the contents of the current viewport (in which case actions like clicking links, clicking buttons, inputting text might be most appropriate, or hovering over element)
    - contents found elsewhere on the full webpage (in which case actions like scrolling, summarization, or full-page Q&A might be most appropriate)
    - on some other website entirely (in which case actions like performing a new web search might be the best option)
"""

WEB_SURFER_OCR_PROMPT = """
Please transcribe all visible text on this page, including both main content and the labels of UI elements.
"""

WEB_SURFER_QA_SYSTEM_MESSAGE = """
You are a helpful assistant that can summarize long documents to answer question.
"""


def WEB_SURFER_QA_PROMPT(title: str, question: str | None = None) -> str:
    base_prompt = f"We are visiting the webpage '{title}'. Its full-text content are pasted below, along with a screenshot of the page's current viewport."
    if question is not None:
        return (
            f"{base_prompt} Please summarize the webpage into one or two paragraphs with respect to '{question}':\n\n"
        )
    else:
        return f"{base_prompt} Please summarize the webpage into one or two paragraphs:\n\n"
