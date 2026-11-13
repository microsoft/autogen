from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Mapping, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .._cancellation_token import CancellationToken


class Decision(Enum):
    """Outcome of a guardrail evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    MODIFY = "modify"


@dataclass
class GuardrailResult:
    """Outcome of a guardrail evaluation.

    Attributes:
        decision: The outcome of the evaluation.
        reason: An optional human-readable explanation for the decision.
            Used when decision is DENY or when callers need to surface why MODIFY was applied.
        modified_args: The revised arguments to pass to the tool, only used when
            decision is MODIFY. When present, the tool receives these instead of the
            original arguments. The modified args are re-validated against the tool's
            schema before execution.
        metadata: Arbitrary additional context from the guardrail evaluation,
            such as audit trail data, policy identifiers, or risk scores.
    """

    decision: Decision
    reason: str | None = None
    modified_args: Mapping[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)  # type: ignore[assignment]


class GuardrailDeniedError(RuntimeError):
    """Raised when a guardrail denies a tool call before execution."""

    def __init__(
        self,
        *,
        tool_name: str,
        result: GuardrailResult,
        arguments: Mapping[str, Any],
    ) -> None:
        self.tool_name = tool_name
        self.result = result
        self.arguments = dict(arguments)
        super().__init__(f"Tool call denied for {tool_name}: {result.reason or 'policy violation'}")


@runtime_checkable
class GuardrailProvider(Protocol):
    """Intercepts tool calls before execution for policy enforcement.

    A guardrail can inspect, modify, or deny a tool call based on the tool name,
    arguments, and execution context. Multiple guardrails may be composed in a chain;
    each receives either the original arguments or the output of the previous guardrail
    in the chain.

    Example:
        A simple rate-limiting guardrail::

            import time
            from collections import defaultdict
            from autogen_core.tools import Decision, GuardrailProvider, GuardrailResult


            class RateLimitGuardrail:
                def __init__(self, max_calls: int = 10, window_seconds: float = 60.0):
                    self._max = max_calls
                    self._window = window_seconds
                    self._calls: dict[str, list[float]] = defaultdict(list)

                async def evaluate(
                    self,
                    *,
                    tool_name: str,
                    args: Mapping[str, Any],
                    agent_name: str | None = None,
                    call_id: str | None = None,
                    cancellation_token: CancellationToken | None = None,
                ) -> GuardrailResult:
                    now = time.monotonic()
                    recent = [t for t in self._calls[tool_name] if now - t < self._window]
                    if len(recent) >= self._max:
                        return GuardrailResult(
                            decision=Decision.DENY,
                            reason=f"Rate limit: {self._max} calls per {self._window}s exceeded",
                        )
                    self._calls[tool_name] = [*recent, now]
                    return GuardrailResult(decision=Decision.ALLOW)

        To attach a guardrail to a tool::

            from autogen_core.tools import FunctionTool


            async def my_tool(arg: str) -> str:
                return f"got: {arg}"


            tool = FunctionTool(my_tool, description="Example tool")
            tool.add_guardrail(RateLimitGuardrail(max_calls=5))
    """

    @abstractmethod
    async def evaluate(
        self,
        *,
        tool_name: str,
        args: Mapping[str, Any],
        agent_name: str | None = None,
        call_id: str | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> GuardrailResult:
        """Evaluate whether a tool call should proceed.

        Args:
            tool_name: Name of the tool being invoked.
            args: Arguments the agent wants to pass to the tool.
            agent_name: Identity of the calling agent, if known.
            call_id: Correlation identifier for the tool call, used for tracing.
            cancellation_token: For cooperative cancellation of long-running evaluations.

        Returns:
            GuardrailResult indicating allow, deny, or modify.

        Note:
            - ALLOW: the tool executes with the arguments as passed (or as modified
              by an earlier guardrail in the chain).
            - DENY: the tool is not called. The denial result, including ``reason``
              and any ``metadata``, is returned to the caller of ``run_json``.
            - MODIFY: the tool is called with ``modified_args`` instead of the
              received ``args``. The modified arguments are re-validated against
              the tool's schema before execution.
        """
        ...
