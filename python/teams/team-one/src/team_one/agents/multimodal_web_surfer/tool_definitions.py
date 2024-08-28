from typing import Any, Dict

# TODO Why does pylance fail if I import from autogen_core.components.tools instead?
from autogen_core.components.tools._base import ParametersSchema, ToolSchema


def _load_tool(tooldef: Dict[str, Any]) -> ToolSchema:
    return ToolSchema(
        name=tooldef["function"]["name"],
        description=tooldef["function"]["description"],
        parameters=ParametersSchema(
            type="object",
            properties=tooldef["function"]["parameters"]["properties"],
            required=tooldef["function"]["parameters"]["required"],
        ),
    )


TOOL_VISIT_URL: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "visit_url",
            "description": "Navigate directly to a provided URL using the browser's address bar. Prefer this tool over other navigation techniques in cases where the user provides a fully-qualified URL (e.g., choose it over clicking links, or inputing queries into search boxes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                    "url": {
                        "type": "string",
                        "description": "The URL to visit in the browser.",
                    },
                },
                "required": ["reasoning", "url"],
            },
        },
    }
)

TOOL_WEB_SEARCH: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Performs a web search on Bing.com with the given query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                    "query": {
                        "type": "string",
                        "description": "The web search query to use.",
                    },
                },
                "required": ["reasoning", "query"],
            },
        },
    }
)

TOOL_HISTORY_BACK: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "history_back",
            "description": "Navigates back one page in the browser's history. This is equivalent to clicking the browser back button.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                },
                "required": ["reasoning"],
            },
        },
    }
)

TOOL_PAGE_UP: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "page_up",
            "description": "Scrolls the entire browser viewport one page UP towards the beginning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                },
                "required": ["reasoning"],
            },
        },
    }
)

TOOL_PAGE_DOWN: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "page_down",
            "description": "Scrolls the entire browser viewport one page DOWN towards the end.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                },
                "required": ["reasoning"],
            },
        },
    }
)

TOOL_CLICK: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Clicks the mouse on the target with the given id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                    "target_id": {
                        "type": "integer",
                        "description": "The numeric id of the target to click.",
                    },
                },
                "required": ["reasoning", "target_id"],
            },
        },
    }
)

TOOL_TYPE: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "input_text",
            "description": "Types the given text value into the specified field.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                    "input_field_id": {
                        "type": "integer",
                        "description": "The numeric id of the input field to receive the text.",
                    },
                    "text_value": {
                        "type": "string",
                        "description": "The text to type into the input field.",
                    },
                },
                "required": ["reasoning", "input_field_id", "text_value"],
            },
        },
    }
)

TOOL_SCROLL_ELEMENT_DOWN: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "scroll_element_down",
            "description": "Scrolls a given html element (e.g., a div or a menu) DOWN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                    "target_id": {
                        "type": "integer",
                        "description": "The numeric id of the target to scroll down.",
                    },
                },
                "required": ["reasoning", "target_id"],
            },
        },
    }
)

TOOL_SCROLL_ELEMENT_UP: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "scroll_element_up",
            "description": "Scrolls a given html element (e.g., a div or a menu) UP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                    "target_id": {
                        "type": "integer",
                        "description": "The numeric id of the target to scroll UP.",
                    },
                },
                "required": ["reasoning", "target_id"],
            },
        },
    }
)

TOOL_READ_PAGE_AND_ANSWER: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "answer_question",
            "description": "Uses AI to answer a question about the current webpage's content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                    "question": {
                        "type": "string",
                        "description": "The question to answer.",
                    },
                },
                "required": ["reasoning", "question"],
            },
        },
    }
)

TOOL_SUMMARIZE_PAGE: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "summarize_page",
            "description": "Uses AI to summarize the entire page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                },
                "required": ["reasoning"],
            },
        },
    }
)

TOOL_SLEEP: ToolSchema = _load_tool(
    {
        "type": "function",
        "function": {
            "name": "sleep",
            "description": "Wait a short period of time. Call this function if the page has not yet fully loaded, or if it is determined that a small delay would increase the task's chances of success.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "A short explanation of the reasoning for calling this tool and taking this action.",
                    },
                },
                "required": ["reasoning"],
            },
        },
    }
)
