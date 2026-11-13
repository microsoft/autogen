"""OPA-authorized tool wrapper for AutoGen BaseTool."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

import httpx
from autogen_core import CancellationToken
from autogen_core.tools import BaseTool

from ._exceptions import OPAAuthorizationError, OPAConnectionError

logger = logging.getLogger(__name__)

_DEFAULT_OPA_TIMEOUT = 5.0


class OPAAuthorizedTool(BaseTool[Any, Any]):
    """A :class:`~autogen_core.tools.BaseTool` wrapper that intercepts every tool call
    and evaluates it against an Open Policy Agent (OPA) policy before execution.

    Works transparently for both regular tool calls and agent-to-agent handoff tools
    (``transfer_to_<AgentName>``), since both ultimately call ``run_json()``.

    Example usage::

        from autogen_ext.tools.opa import opa_authorize_tools

        authorized_tools = opa_authorize_tools(
            [search_tool, delete_tool],
            opa_url="http://localhost:8181",
            context={"user": "alice", "role": "analyst"},
        )
        agent = AssistantAgent(name="PlannerAgent", tools=authorized_tools, ...)

    OPA request body for every call::

        {
            "input": {
                "tool": "<tool_name>",
                "args": { ... },
                "context": { "user": "...", "role": "...", ... }
            }
        }

    OPA must return ``{"result": true}`` to permit the call.
    """

    def __init__(
        self,
        inner_tool: BaseTool[Any, Any],
        *,
        opa_url: str = "http://localhost:8181",
        policy_path: str = "v1/data/autogen/tools/allow",
        context: dict[str, Any] | None = None,
        fail_open: bool = False,
        timeout: float = _DEFAULT_OPA_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """
        Args:
            inner_tool: The real :class:`~autogen_core.tools.BaseTool` to execute when
                authorization succeeds.
            opa_url: Base URL of the OPA server, e.g. ``http://localhost:8181``.
            policy_path: OPA REST API path for the policy rule, e.g.
                ``v1/data/autogen/tools/allow``.
            context: Arbitrary key/value pairs forwarded to OPA as ``input.context``.
                Typical keys: ``user``, ``role``, ``agent_name``, ``session_id``.
            fail_open: If ``True``, allow the tool call when OPA is unreachable.
                If ``False`` (default), deny and raise :class:`OPAConnectionError`.
            timeout: HTTP timeout in seconds for OPA requests (default: 5).
            http_client: Optional pre-configured :class:`httpx.AsyncClient`.
                Primarily useful for testing.
        """
        super().__init__(
            args_type=inner_tool.args_type,
            return_type=inner_tool.return_type,
            name=inner_tool.name,
            description=inner_tool.description,
        )
        self._inner = inner_tool
        self._opa_url = opa_url.rstrip("/")
        self._policy_path = policy_path.lstrip("/")
        self._context: dict[str, Any] = context or {}
        self._fail_open = fail_open
        self._timeout = timeout
        self._http_client = http_client

    async def _query_opa(self, tool_name: str, args: Mapping[str, Any]) -> bool:
        """Send a policy query to OPA and return True if the call is allowed."""
        endpoint = f"{self._opa_url}/{self._policy_path}"
        payload: dict[str, Any] = {
            "input": {
                "tool": tool_name,
                "args": dict(args),
                "context": self._context,
            }
        }
        logger.debug("OPA query: POST %s payload=%s", endpoint, payload)

        try:
            if self._http_client is not None:
                response = await self._http_client.post(endpoint, json=payload, timeout=self._timeout)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(endpoint, json=payload, timeout=self._timeout)

            response.raise_for_status()
            data = response.json()
            allowed: bool = bool(data.get("result", False))
            logger.debug("OPA response: allowed=%s data=%s", allowed, data)
            return allowed

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            if self._fail_open:
                logger.warning(
                    "OPA unreachable at %s — fail_open=True, allowing tool '%s': %s",
                    self._opa_url, tool_name, exc,
                )
                return True
            raise OPAConnectionError(self._opa_url, cause=exc) from exc

        except httpx.HTTPStatusError as exc:
            logger.error("OPA returned HTTP error: %s", exc)
            if self._fail_open:
                return True
            raise OPAConnectionError(self._opa_url, cause=exc) from exc

    async def run_json(
        self,
        args: Mapping[str, Any],
        cancellation_token: CancellationToken,
        call_id: str | None = None,
    ) -> Any:
        """Intercept the tool call, evaluate against OPA, then delegate to the inner tool.

        This is the single dispatch point for *all* tool calls, including
        agent-to-agent handoff tools (``transfer_to_<AgentName>``).
        """
        allowed = await self._query_opa(self.name, args)

        if not allowed:
            logger.info("OPA denied tool call: tool=%s args=%s", self.name, args)
            raise OPAAuthorizationError(
                tool_name=self.name,
                reason="OPA policy evaluation returned false",
            )

        logger.debug("OPA allowed tool call: tool=%s", self.name)
        return await self._inner.run_json(args, cancellation_token, call_id=call_id)

    async def run(self, args: Any, cancellation_token: CancellationToken) -> Any:
        """Satisfy the abstract method requirement — delegation handled by run_json."""
        return await self._inner.run(args, cancellation_token)


def opa_authorize_tools(
    tools: Sequence[BaseTool[Any, Any]],
    *,
    opa_url: str = "http://localhost:8181",
    policy_path: str = "v1/data/autogen/tools/allow",
    context: dict[str, Any] | None = None,
    fail_open: bool = False,
    timeout: float = _DEFAULT_OPA_TIMEOUT,
    http_client: httpx.AsyncClient | None = None,
) -> list[OPAAuthorizedTool]:
    """Wrap a list of tools with OPA authorization.

    This is the recommended entry point for most users::

        from autogen_ext.tools.opa import opa_authorize_tools

        agent = AssistantAgent(
            name="Planner",
            tools=opa_authorize_tools(
                [search_tool, calculator_tool],
                opa_url="http://opa.internal:8181",
                context={"user": "bob", "role": "analyst"},
            ),
        )

    Args:
        tools: Any sequence of :class:`~autogen_core.tools.BaseTool` instances,
            including handoff tools.
        opa_url: OPA server base URL.
        policy_path: OPA REST API policy path.
        context: Key/value pairs forwarded as ``input.context`` in every OPA query.
        fail_open: Allow tool calls when OPA is unreachable (default: False = deny).
        timeout: HTTP timeout in seconds for OPA requests.
        http_client: Optional shared :class:`httpx.AsyncClient` (useful for testing).

    Returns:
        A list of :class:`OPAAuthorizedTool` instances, one per input tool.
    """
    return [
        OPAAuthorizedTool(
            inner_tool=tool,
            opa_url=opa_url,
            policy_path=policy_path,
            context=context,
            fail_open=fail_open,
            timeout=timeout,
            http_client=http_client,
        )
        for tool in tools
    ]
