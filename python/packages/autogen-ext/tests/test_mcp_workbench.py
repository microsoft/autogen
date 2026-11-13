import asyncio
from typing import Any, Mapping

import pytest
from autogen_core import CancellationToken
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from mcp.types import CallToolResult, TextContent


class _FakeActor:
    async def call(self, type: str, args: Mapping[str, Any] | None = None) -> Any:
        assert type == "call_tool"

        async def call_tool() -> CallToolResult:
            await asyncio.sleep(60)
            return CallToolResult(content=[TextContent(type="text", text="done")], isError=False)

        return call_tool()


@pytest.mark.asyncio
async def test_call_tool_links_cancellation_to_actor_coroutine() -> None:
    workbench = McpWorkbench(StdioServerParams(command="unused"))
    workbench._actor = _FakeActor()  # type: ignore[assignment]
    cancellation_token = CancellationToken()

    task = asyncio.create_task(workbench.call_tool("sleep", cancellation_token=cancellation_token))
    await asyncio.sleep(0)
    cancellation_token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
