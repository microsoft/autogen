# Tool Guide

This guide is the canonical reference for tool usage across both **AgentChat** and **Core**.
Use it to decide when to use function tools, built-in tools, or custom tool implementations.

```{note}
For API-level walkthroughs, also see:
- [AgentChat: Using Tools and Workbench](../agentchat-user-guide/tutorial/agents.ipynb#using-tools-and-workbench)
- [Core: Tools Component Guide](../core-user-guide/components/tools.ipynb)
```

## Decision Guide

- Use {py:class}`~autogen_core.tools.FunctionTool` when you want the fastest path from Python function to model-callable tool.
- Use built-in tools from `autogen_ext.tools.*` when they already solve your use case (HTTP, MCP, GraphRAG, code execution wrappers, etc.).
- Implement a custom {py:class}`~autogen_core.tools.BaseTool` when you need full control over execution, schema, state, or serialization.

## FunctionTool

### Sync function

```python
from autogen_core.tools import FunctionTool


def get_weather(city: str, unit: str = "celsius") -> str:
    """Get weather summary for a city."""
    return f"Weather in {city}: 22 degrees {unit}."


weather_tool = FunctionTool(
    get_weather,
    description="Fetch weather for a city.",
)
```

### Async function

```python
from autogen_core import CancellationToken
from autogen_core.tools import FunctionTool


async def lookup_stock(ticker: str, cancellation_token: CancellationToken) -> str:
    """Lookup latest stock price by ticker."""
    # Replace with a real API call.
    return f"{ticker}: 123.45"


stock_tool = FunctionTool(
    lookup_stock,
    description="Lookup latest stock price.",
)
```

### Strict mode

`strict=True` is useful for structured output workflows where all tool arguments must be explicit and required.

```python
strict_tool = FunctionTool(
    lookup_stock,
    description="Lookup latest stock price.",
    strict=True,
)
```

## FunctionTool Design Recommendations

- Keep input schemas shallow and explicit.
- Prefer primitive inputs (`str`, `int`, `bool`, enums) unless nested structure is necessary.
- Add precise type hints for every argument and return type.
- Use clear docstrings and argument descriptions so model clients can build better tool calls.
- Prefer predictable, serializable outputs.
- For end-user responses, returning `str` is often the most robust default.

## Built-in Tools

AutoGen includes many ready-to-use tools in `autogen_ext.tools.*`.

Examples:

- {py:class}`~autogen_ext.tools.http.HttpTool` for REST APIs.
- {py:func}`~autogen_ext.tools.mcp.mcp_server_tools` and MCP workbench for MCP servers.
- {py:class}`~autogen_ext.tools.graphrag.LocalSearchTool` and {py:class}`~autogen_ext.tools.graphrag.GlobalSearchTool` for GraphRAG.
- {py:class}`~autogen_ext.tools.langchain.LangChainToolAdapter` for LangChain adapters.

See the [API reference](../../reference/index.md) for the complete list.

## Custom BaseTool

Use {py:class}`~autogen_core.tools.BaseTool` when you need custom runtime behavior or custom component serialization.

```python
from pydantic import BaseModel, Field
from typing_extensions import Self

from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool


class LookupArgs(BaseModel):
    query: str = Field(description="Search query")


class LookupResult(BaseModel):
    summary: str = Field(description="Lookup summary")


class MyLookupToolConfig(BaseModel):
    endpoint: str


class MyLookupTool(BaseTool[LookupArgs, LookupResult], Component[MyLookupToolConfig]):
    component_type = "tool"
    component_config_schema = MyLookupToolConfig

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        super().__init__(
            args_type=LookupArgs,
            return_type=LookupResult,
            name="my_lookup_tool",
            description="Lookup information from a custom endpoint.",
        )

    async def run(self, args: LookupArgs, cancellation_token: CancellationToken) -> LookupResult:
        # Replace with real I/O using self._endpoint.
        return LookupResult(summary=f"Result for: {args.query}")

    def _to_config(self) -> MyLookupToolConfig:
        return MyLookupToolConfig(endpoint=self._endpoint)

    @classmethod
    def _from_config(cls, config: MyLookupToolConfig) -> Self:
        return cls(endpoint=config.endpoint)
```

## AgentChat and Core Usage

- In **AgentChat**, tools are typically passed to {py:class}`~autogen_agentchat.agents.AssistantAgent`.
- In **Core**, tools can be used directly with model clients or integrated into tool/agent orchestration patterns.

Recommended follow-ups:

- AgentChat tutorial: [Agents and Tools](../agentchat-user-guide/tutorial/agents.ipynb)
- Core component docs: [Tools](../core-user-guide/components/tools.ipynb)
- Core component docs: [Workbench](../core-user-guide/components/workbench.ipynb)
