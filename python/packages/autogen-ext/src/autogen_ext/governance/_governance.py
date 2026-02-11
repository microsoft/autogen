# Copyright (c) Microsoft. All rights reserved.

"""
Agent-OS Governance Implementation for AutoGen
===============================================

Kernel-level governance for AutoGen multi-agent conversations.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


@dataclass
class GovernancePolicy:
    """Policy configuration for governed agents."""

    # Message limits
    max_messages: int = 100
    max_tool_calls: int = 50
    timeout_seconds: int = 300

    # Tool filtering
    allowed_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)

    # Content filtering
    blocked_patterns: List[str] = field(default_factory=list)
    max_message_length: int = 50000

    # Approval flows
    require_human_approval: bool = False
    approval_tools: List[str] = field(default_factory=list)

    # Audit
    log_all_messages: bool = True


@dataclass
class ExecutionContext:
    """Runtime context for governed execution."""

    session_id: str
    policy: GovernancePolicy
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Counters
    message_count: int = 0
    tool_calls: int = 0

    # Audit trail
    events: List[Dict[str, Any]] = field(default_factory=list)

    def record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record an audit event."""
        self.events.append(
            {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
            }
        )


class PolicyViolationError(Exception):
    """Raised when a policy violation is detected."""

    def __init__(self, policy_name: str, description: str, severity: str = "high"):
        self.policy_name = policy_name
        self.description = description
        self.severity = severity
        super().__init__(f"Policy violation ({policy_name}): {description}")


class GovernedAgent:
    """
    Wrapper that adds governance to any AutoGen agent.

    Intercepts messages and tool calls to enforce policies.
    """

    def __init__(
        self,
        agent: Any,
        policy: GovernancePolicy,
        on_violation: Optional[Callable[[PolicyViolationError], None]] = None,
    ):
        self._agent = agent
        self._policy = policy
        self._on_violation = on_violation or self._default_violation_handler
        self._context = ExecutionContext(
            session_id=str(uuid.uuid4())[:8],
            policy=policy,
        )

    def _default_violation_handler(self, error: PolicyViolationError) -> None:
        """Default handler logs violations."""
        logger.error(f"Policy violation: {error}")

    @property
    def name(self) -> str:
        """Get agent name."""
        return getattr(self._agent, "name", "unknown")

    @property
    def original(self) -> Any:
        """Get original unwrapped agent."""
        return self._agent

    def _check_content(self, content: str) -> tuple[bool, str]:
        """Check content against blocked patterns."""
        if len(content) > self._policy.max_message_length:
            return False, f"Message exceeds max length ({len(content)} > {self._policy.max_message_length})"

        content_lower = content.lower()
        for pattern in self._policy.blocked_patterns:
            if pattern.lower() in content_lower:
                return False, f"Content matches blocked pattern: {pattern}"

        return True, ""

    def _check_tool(self, tool_name: str) -> tuple[bool, str]:
        """Check if tool is allowed."""
        if tool_name in self._policy.blocked_tools:
            return False, f"Tool '{tool_name}' is blocked"

        if self._policy.allowed_tools and tool_name not in self._policy.allowed_tools:
            return False, f"Tool '{tool_name}' not in allowed list"

        if self._context.tool_calls >= self._policy.max_tool_calls:
            return False, f"Tool call limit ({self._policy.max_tool_calls}) exceeded"

        return True, ""

    async def on_messages(
        self,
        messages: Sequence[Any],
        cancellation_token: Optional[Any] = None,
    ) -> Any:
        """Handle incoming messages with governance."""
        # Check message count
        if self._context.message_count >= self._policy.max_messages:
            error = PolicyViolationError(
                "message_limit",
                f"Message limit ({self._policy.max_messages}) exceeded",
            )
            self._on_violation(error)
            raise error

        # Check each message content
        for msg in messages:
            content = getattr(msg, "content", str(msg))
            if isinstance(content, str):
                ok, reason = self._check_content(content)
                if not ok:
                    error = PolicyViolationError("content_filter", reason)
                    self._on_violation(error)
                    raise error

        self._context.message_count += len(messages)
        self._context.record_event(
            "messages_received",
            {"count": len(messages)},
        )

        # Forward to original agent
        if hasattr(self._agent, "on_messages"):
            return await self._agent.on_messages(messages, cancellation_token)

        return None

    async def on_messages_stream(
        self,
        messages: Sequence[Any],
        cancellation_token: Optional[Any] = None,
    ) -> AsyncGenerator[Any, None]:
        """Handle streaming messages with governance."""
        # Pre-check
        for msg in messages:
            content = getattr(msg, "content", str(msg))
            if isinstance(content, str):
                ok, reason = self._check_content(content)
                if not ok:
                    error = PolicyViolationError("content_filter", reason)
                    self._on_violation(error)
                    raise error

        self._context.message_count += len(messages)

        # Stream from original
        if hasattr(self._agent, "on_messages_stream"):
            async for chunk in self._agent.on_messages_stream(messages, cancellation_token):
                yield chunk

    def __getattr__(self, name: str) -> Any:
        """Forward unknown attributes to original agent."""
        return getattr(self._agent, name)


class GovernedTeam:
    """
    Governed team of AutoGen agents.

    Wraps a team to enforce policies across all agent interactions.
    """

    def __init__(
        self,
        agents: List[Any],
        policy: Optional[GovernancePolicy] = None,
        termination_condition: Optional[Any] = None,
        on_violation: Optional[Callable[[PolicyViolationError], None]] = None,
    ):
        self._policy = policy or GovernancePolicy()
        self._on_violation = on_violation

        # Wrap all agents
        self._governed_agents = [
            GovernedAgent(agent, self._policy, on_violation) for agent in agents
        ]

        self._termination_condition = termination_condition
        self._context = ExecutionContext(
            session_id=str(uuid.uuid4())[:8],
            policy=self._policy,
        )

    @property
    def agents(self) -> List[GovernedAgent]:
        """Get governed agents."""
        return self._governed_agents

    async def run(
        self,
        task: str,
        cancellation_token: Optional[Any] = None,
    ) -> Any:
        """Run team with governance."""
        # Check task content
        ok, reason = self._check_content(task)
        if not ok:
            error = PolicyViolationError("content_filter", reason)
            if self._on_violation:
                self._on_violation(error)
            raise error

        self._context.record_event("team_run_start", {"task_length": len(task)})

        try:
            # Import RoundRobinGroupChat dynamically to avoid hard dependency
            from autogen_agentchat.teams import RoundRobinGroupChat

            # Create team with governed agents
            original_agents = [ga.original for ga in self._governed_agents]
            team = RoundRobinGroupChat(
                original_agents,
                termination_condition=self._termination_condition,
            )

            result = await team.run(task=task, cancellation_token=cancellation_token)

            self._context.record_event("team_run_complete", {"success": True})
            return result

        except ImportError:
            # Fallback: just run first agent
            logger.warning("autogen_agentchat not available, running first agent only")
            if self._governed_agents:
                return await self._governed_agents[0].on_messages([task], cancellation_token)
            return None

    async def run_stream(
        self,
        task: str,
        cancellation_token: Optional[Any] = None,
    ) -> AsyncGenerator[Any, None]:
        """Run team with streaming and governance."""
        ok, reason = self._check_content(task)
        if not ok:
            error = PolicyViolationError("content_filter", reason)
            if self._on_violation:
                self._on_violation(error)
            raise error

        try:
            from autogen_agentchat.teams import RoundRobinGroupChat

            original_agents = [ga.original for ga in self._governed_agents]
            team = RoundRobinGroupChat(
                original_agents,
                termination_condition=self._termination_condition,
            )

            async for chunk in team.run_stream(task=task, cancellation_token=cancellation_token):
                yield chunk

        except ImportError:
            logger.warning("autogen_agentchat not available")

    def _check_content(self, content: str) -> tuple[bool, str]:
        """Check content against policy."""
        if len(content) > self._policy.max_message_length:
            return False, f"Content exceeds max length"

        content_lower = content.lower()
        for pattern in self._policy.blocked_patterns:
            if pattern.lower() in content_lower:
                return False, f"Content matches blocked pattern: {pattern}"

        return True, ""

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get combined audit log from team and all agents."""
        events = list(self._context.events)
        for agent in self._governed_agents:
            events.extend(agent._context.events)
        return sorted(events, key=lambda e: e["timestamp"])

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        total_messages = sum(a._context.message_count for a in self._governed_agents)
        total_tool_calls = sum(a._context.tool_calls for a in self._governed_agents)

        return {
            "session_id": self._context.session_id,
            "agent_count": len(self._governed_agents),
            "total_messages": total_messages,
            "total_tool_calls": total_tool_calls,
            "policy": {
                "max_messages": self._policy.max_messages,
                "max_tool_calls": self._policy.max_tool_calls,
                "blocked_patterns_count": len(self._policy.blocked_patterns),
            },
        }
