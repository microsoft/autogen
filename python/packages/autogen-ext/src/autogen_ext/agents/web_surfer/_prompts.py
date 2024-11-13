WEB_SURFER_TOOL_PROMPT = """
Consider the following screenshot of a web browser, which is open to the page '{url}'. In this screenshot, interactive elements are outlined in bounding boxes of different colors. Each bounding box has a numeric ID label in the same color. Additional information about each visible label is listed below:

{visible_targets}{other_targets_str}{focused_hint}You are to respond to the user's most recent request by selecting an appropriate tool the following set, or by answering the question directly if possible:

{tool_names}

When deciding between tools, consider if the request can be best addressed by:
    - the contents of the current viewport (in which case actions like clicking links, clicking buttons, or inputting text might be most appropriate)
    - contents found elsewhere on the full webpage (in which case actions like scrolling, summarization, or full-page Q&A might be most appropriate)
    - on some other website entirely (in which case actions like performing a new web search might be the best option)
"""

WEB_SURFER_OCR_PROMPT = "Please transcribe all visible text on this page, including both main content and the labels of UI elements."