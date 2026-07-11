---
myst:
  html_meta:
    "description lang=en": |
      Guide to using tools in AutoGen, including FunctionTool, built-in tools, and custom BaseTool implementations.
---

# Tool Guide

Tools extend the capabilities of AI agents by allowing them to perform actions beyond text generation, such as calling APIs, querying databases, executing code, and interacting with external services.

This guide covers how to define, use, and create tools in AutoGen.

(function-tool)=

## FunctionTool

{py:class}`~autogen_core.tools.FunctionTool` is the simplest way to create a tool. It wraps a Python function and converts it into a tool usable by agents.

### Defining a FunctionTool (Sync)

```python
from autogen_core.tools import FunctionTool

def web_search_func(query: str) -> str:
    """Search the web for information.

    Args:
        query: The search query string.

    Returns:
        Search result as a string.
    """
    return f"Mock result for: {query}"

web_search_tool = FunctionTool(
    web_search_func,
    description="Search the web for information",
)
```

### Defining a FunctionTool (Async)

For async functions, use the same {py:class}`~autogen_core.tools.FunctionTool` wrapper:

```python
import asyncio
from autogen_core.tools import FunctionTool

async def async_fetch_data(url: str) -> str:
    """Fetch data from a URL.

    Args:
        url: The URL to fetch data from.

    Returns:
        Response content as a string.
    """
    await asyncio.sleep(0.1)
    return f"Mock data from: {url}"

fetch_tool = FunctionTool(
    async_fetch_data,
    description="Fetch data from a URL",
)
```

### How it Works

When you wrap a function in {py:class}`~autogen_core.tools.FunctionTool`, AutoGen:

1. **Inspects the function signature** to extract parameter names, types, and defaults.
2. **Parses the docstring** to generate descriptions for each parameter.
3. **Generates a JSON schema** that the model can understand (OpenAI-style function calling format).
4. **Validates and routes** incoming tool call arguments to the function at runtime.

### Parameter Design Recommendations

- **Keep parameters simple**: Use primitive types (`str`, `int`, `float`, `bool`) as much as possible.
- **Avoid nested types**: Avoid dictionaries, complex objects, or deeply nested structures as input parameters.
- **Use few parameters**: The fewer parameters a function has, the more reliably the model will call it correctly.
- **Provide clear names**: Parameter names should be self-explanatory about their purpose.

### Return Type Recommendations

- **Use strings** as the return type whenever possible. Most models handle string responses most reliably.
- **Use serializable types**: If returning structured data, use types that can be serialized to JSON (dicts, lists, strings, numbers).
- **Include enough context**: Return results that include enough information for the model to make decisions without needing extra tool calls.

### Type Hints and Docstrings

Type hints and docstrings are essential because AutoGen uses them to generate the tool schema that the model sees:

```python
from typing import Optional
from dataclasses import dataclass

def calculate_discount(
    price: float,
    discount_percent: float,
    coupon_code: Optional[str] = None,
) -> str:
    """Calculate the discounted price.

    Args:
        price: The original price of the item.
        discount_percent: The discount percentage (0-100).
        coupon_code: An optional coupon code for additional discount.

    Returns:
        A string describing the final price and any discounts applied.
    """
    # implementation...
    return f"Final price: ${price * (1 - discount_percent / 100):.2f}"
```

**Best practices:**
- Always add type hints to function parameters and return values.
- Write clear docstrings with parameter descriptions.
- Use `Optional[X]` for nullable parameters instead of `X = None` without typing.
- Include a clear description parameter when creating the {py:class}`~autogen_core.tools.FunctionTool`.

(built-in-tools)=

## Built-in Tools

AutoGen provides several built-in tools in the `autogen_ext.tools` package. These include:

| Tool | Description |
|------|-------------|
| {py:class}`~autogen_ext.tools.graphrag.LocalSearchTool` | Tool for GraphRAG-based local search |
| {py:func}`~autogen_ext.tools.mcp.mcp_server_tools` | Tools served from an MCP (Model Context Protocol) server |
| {py:class}`~autogen_ext.tools.semantic_kernel.SKPluginTool` | Tools wrapping Semantic Kernel plugins |

See the [API Reference](https://microsoft.github.io/autogen/stable/reference/index.html) for the complete list of built-in tools and their documentation.

### Using Tools in AgentChat

In AgentChat, you can use {py:class}`~autogen_agentchat.agents.AssistantAgent` with tools:

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o")

agent = AssistantAgent(
    name="assistant",
    model_client=model_client,
    tools=[web_search_tool],
)
```

### Using Tools in Core

In Core, tools are passed through the function call context:

```python
from autogen_core import FunctionTool

tool = FunctionTool(web_search_func, description="Search the web")
# Tools are resolved through the ToolAgent or directly invoked
```

(custom-base-tool)=

## Custom BaseTool Implementation

For advanced use cases, you can implement a custom tool by subclassing {py:class}`~autogen_core.tools.BaseTool`.

### Example: Custom BaseTool

```python
from typing import Any, Dict, Tuple, get_type_hints
from autogen_core.tools import BaseTool
from pydantic import BaseModel


class WeatherToolConfig(BaseModel):
    api_key: str
    units: str = "metric"


class WeatherTool(BaseTool[Tuple[str], str]):
    """A custom weather tool."""

    def __init__(self, config: WeatherToolConfig):
        self._config = config
        super().__init__(
            args_type=Tuple[str],
            return_type=str,
        )

    def run(self, args: Tuple[str]) -> str:
        """Get weather for a city.

        Args:
            args: A tuple containing (city_name,).

        Returns:
            Weather information as a string.
        """
        city = args[0]
        # In production, call a real API
        return f"Weather in {city}: 22°C, {self._config.units}"

    async def run_json(self, json_args: Dict[str, Any]) -> str:
        city = json_args["city"]
        return self.run((city,))
```

### Serializable Configuration

When creating custom tools, use Pydantic models for configuration to enable serialization:

```python
from pydantic import BaseModel


class DatabaseToolConfig(BaseModel):
    connection_string: str
    timeout: int = 30
    max_retries: int = 3


class DatabaseQueryTool(BaseTool[Tuple[str], str]):
    def __init__(self, config: DatabaseToolConfig):
        self._config = config
        super().__init__(args_type=Tuple[str], return_type=str)
```

Using Pydantic `BaseModel` for configuration ensures your tool can be serialized, deserialized, and properly validated.

## Next Steps

- See the [agents tutorial](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html) for more examples of using tools in AgentChat.
- See the [Core tools documentation](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/components/tools.html) for lower-level tool usage.
- Browse the [API Reference](https://microsoft.github.io/autogen/stable/reference/index.html) for all available tools.
