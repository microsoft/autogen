from autogen_core.components.tools import ParametersSchema, ToolSchema

TOOL_OPEN_LOCAL_FILE = ToolSchema(
    name="open_local_file",
    description="Open a local file at a path in the text-based browser and return current viewport content.",
    parameters=ParametersSchema(
        type="object",
        properties={
            "path": {
                "type": "string",
                "description": "The relative or absolute path of a local file to visit.",
            },
        },
        required=["path"],
    ),
)


TOOL_PAGE_UP = ToolSchema(
    name="page_up",
    description="Scroll the viewport UP one page-length in the current file and return the new viewport content.",
)


TOOL_PAGE_DOWN = ToolSchema(
    name="page_down",
    description="Scroll the viewport DOWN one page-length in the current file and return the new viewport content.",
)


TOOL_FIND_ON_PAGE_CTRL_F = ToolSchema(
    name="find_on_page_ctrl_f",
    description="Scroll the viewport to the first occurrence of the search string. This is equivalent to Ctrl+F.",
    parameters=ParametersSchema(
        type="object",
        properties={
            "search_string": {
                "type": "string",
                "description": "The string to search for on the page. This search string supports wildcards like '*'",
            },
        },
        required=["search_string"],
    ),
)


TOOL_FIND_NEXT = ToolSchema(
    name="find_next",
    description="Scroll the viewport to next occurrence of the search string.",
)
