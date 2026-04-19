"""Unit tests for OPAAuthorizedTool — no real OPA server required."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool

from autogen_ext.tools.opa import OPAAuthorizedTool, opa_authorize_tools
from autogen_ext.tools.opa._exceptions import OPAAuthorizationError, OPAConnectionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _EchoTool(BaseTool[Any, Any]):
    """Minimal BaseTool that echoes its args."""

    def __init__(self, name: str = "echo_tool") -> None:
        super().__init__(
            args_type=dict,
            return_type=dict,
            name=name,
            description="Echo args back",
        )

    async def run(self, args: Any, cancellation_token: CancellationToken) -> Any:
        return {"echoed": dict(args)}


def _opa_response(allowed: bool) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"result": allowed}
    resp.raise_for_status = MagicMock()
    return resp


def _make_tool(
    inner: BaseTool | None = None,
    *,
    allowed: bool = True,
    fail_open: bool = False,
    connect_error: bool = False,
    name: str = "echo_tool",
) -> tuple[OPAAuthorizedTool, AsyncMock]:
    inner = inner or _EchoTool(name=name)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    if connect_error:
        mock_client.post.side_effect = httpx.ConnectError("refused")
    else:
        mock_client.post.return_value = _opa_response(allowed)
    tool = OPAAuthorizedTool(
        inner_tool=inner,
        opa_url="http://opa-test:8181",
        context={"user": "alice", "role": "analyst"},
        fail_open=fail_open,
        http_client=mock_client,
    )
    return tool, mock_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_allowed_executes_inner_tool() -> None:
    tool, mock_client = _make_tool(allowed=True)
    result = await tool.run_json({"x": 1}, CancellationToken())
    assert result == {"echoed": {"x": 1}}
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_denied_raises_authorization_error() -> None:
    inner = _EchoTool()
    inner.run = AsyncMock()  # must NOT be called
    tool, _ = _make_tool(inner=inner, allowed=False)
    with pytest.raises(OPAAuthorizationError) as exc_info:
        await tool.run_json({"x": 1}, CancellationToken())
    assert exc_info.value.tool_name == "echo_tool"
    inner.run.assert_not_called()


@pytest.mark.asyncio
async def test_fail_open_true_allows_when_opa_down() -> None:
    tool, _ = _make_tool(fail_open=True, connect_error=True)
    result = await tool.run_json({"x": 99}, CancellationToken())
    assert result == {"echoed": {"x": 99}}


@pytest.mark.asyncio
async def test_fail_open_false_raises_when_opa_down() -> None:
    tool, _ = _make_tool(fail_open=False, connect_error=True)
    with pytest.raises(OPAConnectionError) as exc_info:
        await tool.run_json({"x": 1}, CancellationToken())
    assert "opa-test" in str(exc_info.value)


@pytest.mark.asyncio
async def test_opa_authorize_tools_wraps_list() -> None:
    tools = [_EchoTool("a"), _EchoTool("b"), _EchoTool("c")]
    authorized = opa_authorize_tools(tools, opa_url="http://opa:8181")
    assert len(authorized) == 3
    assert all(isinstance(t, OPAAuthorizedTool) for t in authorized)
    assert [t.name for t in authorized] == ["a", "b", "c"]
    assert authorized[0]._inner is tools[0]


@pytest.mark.asyncio
async def test_handoff_tool_intercepted() -> None:
    handoff = _EchoTool(name="transfer_to_CoderAgent")
    tool, mock_client = _make_tool(inner=handoff, allowed=True, name="transfer_to_CoderAgent")
    await tool.run_json({}, CancellationToken())
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["input"]["tool"] == "transfer_to_CoderAgent"


@pytest.mark.asyncio
async def test_handoff_denied_by_opa() -> None:
    handoff = _EchoTool(name="transfer_to_EvilAgent")
    tool, _ = _make_tool(inner=handoff, allowed=False, name="transfer_to_EvilAgent")
    with pytest.raises(OPAAuthorizationError) as exc_info:
        await tool.run_json({}, CancellationToken())
    assert exc_info.value.tool_name == "transfer_to_EvilAgent"


@pytest.mark.asyncio
async def test_opa_payload_structure() -> None:
    tool, mock_client = _make_tool(allowed=True, name="read_file")
    await tool.run_json({"path": "/tmp/report.txt"}, CancellationToken())
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload == {
        "input": {
            "tool": "read_file",
            "args": {"path": "/tmp/report.txt"},
            "context": {"user": "alice", "role": "analyst"},
        }
    }


@pytest.mark.asyncio
async def test_call_id_forwarded() -> None:
    inner = _EchoTool()
    inner.run_json = AsyncMock(return_value={"echoed": {}})
    tool, mock_client = _make_tool(inner=inner, allowed=True)
    await tool.run_json({}, CancellationToken(), call_id="call-abc123")
    inner.run_json.assert_called_once()
    _, _, kwargs = inner.run_json.call_args[0], inner.run_json.call_args[1], inner.run_json.call_args[1]
    assert inner.run_json.call_args[1].get("call_id") == "call-abc123" or            inner.run_json.call_args[0][2] == "call-abc123"


def test_exception_messages() -> None:
    err = OPAAuthorizationError("delete_file", reason="policy denied")
    assert "delete_file" in str(err)
    assert "policy denied" in str(err)

    conn_err = OPAConnectionError("http://opa:8181")
    assert "http://opa:8181" in str(conn_err)


def test_tool_name_preserved() -> None:
    inner = _EchoTool(name="my_special_tool")
    tool, _ = _make_tool(inner=inner, name="my_special_tool")
    assert tool.name == "my_special_tool"
    assert tool.description == inner.description
