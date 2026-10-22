import re

with open("python/packages/autogen-ext/src/autogen_ext/models/cache/_chat_completion_cache.py", "r") as f:
    content = f.read()

# Update _check_cache signature
content = re.sub(
    r'def _check_cache\(\s*self,\s*messages: Sequence\[LLMMessage\],\s*tools: Sequence\[Tool \| ToolSchema\],\s*json_output: Optional\[bool \| type\[BaseModel\]\],\s*extra_create_args: Mapping\[str, Any\],\s*\) ->',
    'def _check_cache(\n        self,\n        messages: Sequence[LLMMessage],\n        tools: Sequence[Tool | ToolSchema],\n        tool_choice: Tool | str | None,\n        json_output: Optional[bool | type[BaseModel]],\n        extra_create_args: Mapping[str, Any],\n    ) ->',
    content
)

# Update data dict
content = re.sub(
    r'"tools": \[\(tool\.schema if isinstance\(tool, Tool\) else tool\) for tool in tools\],',
    '"tools": [(tool.schema if isinstance(tool, Tool) else tool) for tool in tools],\n            "tool_choice": tool_choice.schema if isinstance(tool_choice, Tool) else tool_choice,',
    content
)

# Update calls
content = re.sub(
    r'self\._check_cache\(messages, tools, json_output, extra_create_args\)',
    'self._check_cache(messages, tools, tool_choice, json_output, extra_create_args)',
    content
)
content = re.sub(
    r'self\._check_cache\(\n\s*messages, tools, json_output, extra_create_args\n\s*\)',
    'self._check_cache(messages, tools, tool_choice, json_output, extra_create_args)',
    content
)


with open("python/packages/autogen-ext/src/autogen_ext/models/cache/_chat_completion_cache.py", "w") as f:
    f.write(content)
