TOOL_VISIT_URL = {
    "type": "function",
    "function": {
        "name": "visit_url",
        "description": "Inputs the given url into the browser's address bar, navigating directly to the requested page.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to visit in the browser.",
                },
            },
            "required": ["url"],
        },
    },
}

TOOL_WEB_SEARCH = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Performs a web search on Bing.com with the given query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The web search query to use.",
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_HISTORY_BACK = {
    "type": "function",
    "function": {
        "name": "history_back",
        "description": "Navigates back one page in the browser's history. This is equivalent to clicking the browser back button.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

TOOL_PAGE_UP = {
    "type": "function",
    "function": {
        "name": "page_up",
        "description": "Scrolls the entire browser viewport one page UP towards the beginning.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

TOOL_PAGE_DOWN = {
    "type": "function",
    "function": {
        "name": "page_down",
        "description": "Scrolls the entire browser viewport one page DOWN towards the end.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

TOOL_CLICK = {
    "type": "function",
    "function": {
        "name": "click",
        "description": "Clicks the mouse on the target with the given id.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "integer",
                    "description": "The numeric id of the target to click.",
                },
            },
            "required": ["target_id"],
        },
    },
}

TOOL_TYPE = {
    "type": "function",
    "function": {
        "name": "input_text",
        "description": "Types the given text value into the specified field.",
        "parameters": {
            "type": "object",
            "properties": {
                "input_field_id": {
                    "type": "integer",
                    "description": "The numeric id of the input field to receive the text.",
                },
                "text_value": {
                    "type": "string",
                    "description": "The text to type into the input field.",
                },
            },
            "required": ["input_field_id", "text_value"],
        },
    },
}

TOOL_SCROLL_ELEMENT_DOWN = {
    "type": "function",
    "function": {
        "name": "scroll_element_down",
        "description": "Scrolls a given html element (e.g., a div or a menu) DOWN.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "integer",
                    "description": "The numeric id of the target to scroll down.",
                },
            },
            "required": ["target_id"],
        },
    },
}

TOOL_SCROLL_ELEMENT_UP = {
    "type": "function",
    "function": {
        "name": "scroll_element_up",
        "description": "Scrolls a given html element (e.g., a div or a menu) UP.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_id": {
                    "type": "integer",
                    "description": "The numeric id of the target to scroll UP.",
                },
            },
            "required": ["target_id"],
        },
    },
}
