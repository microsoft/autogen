"""
SHACKLE Termination Condition for AutoGen
==========================================
Budget-enforcing, loop-detecting termination condition for AutoGen agents.

Usage:
    from autogen_agentchat.conditions import ShackleGuard
    guard = ShackleGuard(budget=0.25, max_repeat_calls=3)
    team.run(task, termination_condition=guard)
"""

from __future__ import annotations

import time
from typing import Sequence

from autogen_core import Component
from pydantic import BaseModel
from typing_extensions import Self

from ..base import TerminatedException, TerminationCondition
from ..messages import (
    BaseAgentEvent,
    BaseChatMessage,
    StopMessage,
    ToolCallExecutionEvent,
    ToolCallRequestEvent,
)


class ShackleGuardConfig(BaseModel):
    budget: float = 0.25
    max_repeat_calls: int = 3
    error_amplification: bool = True
    timeout_seconds: int = 300


class ShackleGuard(TerminationCondition, Component[ShackleGuardConfig]):
    """Pre-execution circuit breaker for AutoGen teams.

    Monitors tool calls across all agents in a team, enforces budgets,
    detects runaway loops, and terminates the conversation when limits
    are exceeded.

    Implements the tri-state pattern:
    - ALLOW: continue execution
    - TERMINATE: circuit tripped, stop the team
    - WARN: budget running low (human-readable warning in StopMessage)

    Args:
        budget: Maximum cumulative cost in USD before circuit opens
        max_repeat_calls: Max identical tool calls before termination
        error_amplification: Tighten limits on 401/403/500 error signals
        timeout_seconds: Wall-clock timeout for the entire session
    """

    component_config_schema = ShackleGuardConfig
    component_provider_override = "autogen_agentchat.conditions.ShackleGuard"

    def __init__(
        self,
        budget: float = 0.25,
        max_repeat_calls: int = 3,
        error_amplification: bool = True,
        timeout_seconds: int = 300,
    ) -> None:
        self._budget = budget
        self._max_repeat_calls = max_repeat_calls
        self._error_amplification = error_amplification
        self._timeout_seconds = timeout_seconds

        self._budget_spent: float = 0.0
        self._total_calls: int = 0
        self._repeat_counts: dict[str, int] = {}
        self._last_tool: str = ""
        self._last_args: str = ""
        self._circuit_tripped: bool = False
        self._circuit_reason: str = ""
        self._start_time: float = time.time()

        self._error_signals = (
            "401", "unauthorized", "403", "forbidden", "500",
            "internal server error", "timeout", "rate limit",
            "quota exceeded", "token expired", "connection refused",
        )

    @property
    def terminated(self) -> bool:
        return self._circuit_tripped

    async def __call__(
        self, messages: Sequence[BaseAgentEvent | BaseChatMessage]
    ) -> StopMessage | None:
        if self._circuit_tripped:
            raise TerminatedException("SHACKLE circuit already tripped")

        for msg in messages:
            # Check tool call requests (before execution)
            if isinstance(msg, ToolCallRequestEvent):
                for tc in msg.content:
                    result = self._evaluate_request(tc.name, tc.arguments)
                    if result:
                        return result

            # Check tool execution results (after execution)
            if isinstance(msg, ToolCallExecutionEvent):
                for tc in msg.content:
                    result = self._evaluate_result(tc.name, str(tc.content))
                    if result:
                        return result

        return None

    def _evaluate_request(
        self, tool_name: str, args: str
    ) -> StopMessage | None:
        """Evaluate a tool call BEFORE execution."""
        # Timeout check
        if time.time() - self._start_time > self._timeout_seconds:
            self._circuit_tripped = True
            self._circuit_reason = f"SHACKLE: session timeout ({self._timeout_seconds}s)"
            return StopMessage(content=self._circuit_reason, source="ShackleGuard")

        # Budget check
        remaining = self._budget - self._budget_spent
        if remaining <= 0:
            self._circuit_tripped = True
            self._circuit_reason = (
                f"SHACKLE: budget exhausted "
                f"(${self._budget_spent:.4f} / ${self._budget:.2f})"
            )
            return StopMessage(content=self._circuit_reason, source="ShackleGuard")

        # Repeat detection
        args_hash = str(hash(args))
        is_repeat = tool_name == self._last_tool and args_hash == self._last_args
        if is_repeat:
            self._repeat_counts[tool_name] = self._repeat_counts.get(tool_name, 0) + 1
            limit = self._max_repeat_calls

            if self._error_amplification and self._error_in_args(args):
                limit = max(1, limit - 1)

            if self._repeat_counts[tool_name] >= limit:
                self._circuit_tripped = True
                self._circuit_reason = (
                    f"SHACKLE: loop detected — "
                    f"'{tool_name}' called {self._repeat_counts[tool_name]}x"
                )
                return StopMessage(content=self._circuit_reason, source="ShackleGuard")
        else:
            self._repeat_counts[tool_name] = 1

        self._last_tool = tool_name
        self._last_args = args_hash
        return None

    def _evaluate_result(
        self, tool_name: str, content: str
    ) -> StopMessage | None:
        """Evaluate a tool result AFTER execution for error signals."""
        if self._error_amplification and self._error_in_args(content):
            # Error detected in result — amplify repeat limits
            self._repeat_counts[tool_name] = self._repeat_counts.get(tool_name, 0) + 1

        # Cost tracking
        cost = {
            "web_search": 0.001, "read_file": 0.0001,
            "write_file": 0.0005, "execute_code": 0.005,
            "call_api": 0.003, "query_db": 0.002,
        }.get(tool_name, 0.001)

        self._budget_spent += cost
        self._total_calls += 1
        return None

    def _error_in_args(self, text: str) -> bool:
        return any(s in text.lower() for s in self._error_signals)

    async def reset(self) -> None:
        self._budget_spent = 0.0
        self._total_calls = 0
        self._repeat_counts = {}
        self._circuit_tripped = False
        self._circuit_reason = ""
        self._start_time = time.time()

    def _to_config(self) -> ShackleGuardConfig:
        return ShackleGuardConfig(
            budget=self._budget,
            max_repeat_calls=self._max_repeat_calls,
            error_amplification=self._error_amplification,
            timeout_seconds=self._timeout_seconds,
        )

    @classmethod
    def _from_config(cls, config: ShackleGuardConfig) -> Self:
        return cls(
            budget=config.budget,
            max_repeat_calls=config.max_repeat_calls,
            error_amplification=config.error_amplification,
            timeout_seconds=config.timeout_seconds,
        )
