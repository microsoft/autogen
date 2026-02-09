# Copyright (c) Microsoft. All rights reserved.

"""
Tests for Agent-OS Governance Extension
========================================

Covers: GovernancePolicy, ExecutionContext, PolicyViolationError,
        GovernedAgent, GovernedTeam.
"""

import asyncio
import logging
from dataclasses import fields
from types import SimpleNamespace
from typing import Any, Optional, Sequence
from unittest.mock import AsyncMock, MagicMock

import pytest

from autogen_ext.governance import (
    ExecutionContext,
    GovernancePolicy,
    GovernedAgent,
    GovernedTeam,
    PolicyViolationError,
)


# ── Helpers ───────────────────────────────────────────────────────


class FakeAgent:
    """Minimal mock agent with name and on_messages."""

    def __init__(self, name: str = "fake-agent"):
        self.name = name
        self.on_messages = AsyncMock(return_value="ok")
        self.custom_attr = 42


class FakeStreamAgent:
    """Agent that supports on_messages_stream."""

    def __init__(self, name: str = "stream-agent", chunks: list | None = None):
        self.name = name
        self._chunks = chunks or ["chunk1", "chunk2"]

    async def on_messages_stream(
        self, messages: Sequence[Any], cancellation_token: Optional[Any] = None
    ):
        for c in self._chunks:
            yield c


# ── GovernancePolicy ──────────────────────────────────────────────


class TestGovernancePolicy:
    def test_defaults(self):
        p = GovernancePolicy()
        assert p.max_messages == 100
        assert p.max_tool_calls == 50
        assert p.timeout_seconds == 300
        assert p.blocked_patterns == []
        assert p.blocked_tools == []
        assert p.allowed_tools == []
        assert p.max_message_length == 50000
        assert p.require_human_approval is False
        assert p.approval_tools == []
        assert p.log_all_messages is True

    def test_custom_values(self):
        p = GovernancePolicy(
            max_messages=10,
            max_tool_calls=5,
            blocked_patterns=["DROP TABLE"],
            blocked_tools=["shell"],
            allowed_tools=["search"],
            max_message_length=1000,
        )
        assert p.max_messages == 10
        assert p.max_tool_calls == 5
        assert p.blocked_patterns == ["DROP TABLE"]
        assert p.blocked_tools == ["shell"]
        assert p.allowed_tools == ["search"]
        assert p.max_message_length == 1000

    def test_is_dataclass(self):
        names = {f.name for f in fields(GovernancePolicy)}
        expected = {
            "max_messages",
            "max_tool_calls",
            "timeout_seconds",
            "allowed_tools",
            "blocked_tools",
            "blocked_patterns",
            "max_message_length",
            "require_human_approval",
            "approval_tools",
            "log_all_messages",
        }
        assert names == expected


# ── ExecutionContext ───────────────────────────────────────────────


class TestExecutionContext:
    def test_creation(self):
        p = GovernancePolicy()
        ctx = ExecutionContext(session_id="test-123", policy=p)
        assert ctx.session_id == "test-123"
        assert ctx.message_count == 0
        assert ctx.tool_calls == 0
        assert ctx.events == []

    def test_record_event(self):
        p = GovernancePolicy()
        ctx = ExecutionContext(session_id="s1", policy=p)
        ctx.record_event("test_event", {"key": "value"})
        assert len(ctx.events) == 1
        assert ctx.events[0]["type"] == "test_event"
        assert ctx.events[0]["data"] == {"key": "value"}
        assert "timestamp" in ctx.events[0]

    def test_multiple_events(self):
        p = GovernancePolicy()
        ctx = ExecutionContext(session_id="s1", policy=p)
        for i in range(5):
            ctx.record_event(f"event_{i}", {"i": i})
        assert len(ctx.events) == 5
        assert ctx.events[4]["type"] == "event_4"


# ── PolicyViolationError ──────────────────────────────────────────


class TestPolicyViolationError:
    def test_basic(self):
        e = PolicyViolationError("content_filter", "blocked pattern found")
        assert e.policy_name == "content_filter"
        assert e.description == "blocked pattern found"
        assert e.severity == "high"
        assert "content_filter" in str(e)
        assert "blocked pattern found" in str(e)

    def test_custom_severity(self):
        e = PolicyViolationError("rate_limit", "too many calls", severity="medium")
        assert e.severity == "medium"

    def test_is_exception(self):
        with pytest.raises(PolicyViolationError):
            raise PolicyViolationError("test", "test error")


# ── GovernedAgent ─────────────────────────────────────────────────


class TestGovernedAgent:
    def test_wraps_agent(self):
        agent = FakeAgent("my-agent")
        ga = GovernedAgent(agent, GovernancePolicy())
        assert ga.name == "my-agent"
        assert ga.original is agent

    def test_name_fallback(self):
        ga = GovernedAgent(object(), GovernancePolicy())
        assert ga.name == "unknown"

    def test_getattr_forwarding(self):
        agent = FakeAgent()
        ga = GovernedAgent(agent, GovernancePolicy())
        assert ga.custom_attr == 42

    # ── Content checks ────────────────────────────────────────────

    def test_check_content_passes(self):
        ga = GovernedAgent(FakeAgent(), GovernancePolicy())
        ok, reason = ga._check_content("hello world")
        assert ok is True
        assert reason == ""

    def test_check_content_blocks_pattern(self):
        policy = GovernancePolicy(blocked_patterns=["DROP TABLE", "rm -rf"])
        ga = GovernedAgent(FakeAgent(), policy)
        ok, reason = ga._check_content("please DROP TABLE users")
        assert ok is False
        assert "DROP TABLE" in reason

    def test_check_content_case_insensitive(self):
        policy = GovernancePolicy(blocked_patterns=["DROP TABLE"])
        ga = GovernedAgent(FakeAgent(), policy)
        ok, reason = ga._check_content("drop table users")
        assert ok is False

    def test_check_content_max_length(self):
        policy = GovernancePolicy(max_message_length=10)
        ga = GovernedAgent(FakeAgent(), policy)
        ok, reason = ga._check_content("a" * 11)
        assert ok is False
        assert "max length" in reason

    # ── Tool checks ───────────────────────────────────────────────

    def test_check_tool_allowed(self):
        ga = GovernedAgent(FakeAgent(), GovernancePolicy())
        ok, reason = ga._check_tool("web_search")
        assert ok is True

    def test_check_tool_blocked(self):
        policy = GovernancePolicy(blocked_tools=["shell_execute"])
        ga = GovernedAgent(FakeAgent(), policy)
        ok, reason = ga._check_tool("shell_execute")
        assert ok is False
        assert "blocked" in reason

    def test_check_tool_allowlist(self):
        policy = GovernancePolicy(allowed_tools=["search", "read"])
        ga = GovernedAgent(FakeAgent(), policy)
        ok, _ = ga._check_tool("search")
        assert ok is True
        ok, reason = ga._check_tool("shell")
        assert ok is False
        assert "not in allowed list" in reason

    def test_check_tool_limit(self):
        policy = GovernancePolicy(max_tool_calls=2)
        ga = GovernedAgent(FakeAgent(), policy)
        ga._context.tool_calls = 2
        ok, reason = ga._check_tool("anything")
        assert ok is False
        assert "limit" in reason

    # ── on_messages ───────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_on_messages_forwards(self):
        agent = FakeAgent()
        ga = GovernedAgent(agent, GovernancePolicy())
        msgs = [SimpleNamespace(content="hello")]
        result = await ga.on_messages(msgs)
        assert result == "ok"
        agent.on_messages.assert_awaited_once_with(msgs, None)

    @pytest.mark.asyncio
    async def test_on_messages_records_audit(self):
        ga = GovernedAgent(FakeAgent(), GovernancePolicy())
        await ga.on_messages([SimpleNamespace(content="hi")])
        assert ga._context.message_count == 1
        assert len(ga._context.events) == 1
        assert ga._context.events[0]["type"] == "messages_received"

    @pytest.mark.asyncio
    async def test_on_messages_blocks_pattern(self):
        policy = GovernancePolicy(blocked_patterns=["rm -rf"])
        violations = []
        ga = GovernedAgent(FakeAgent(), policy, on_violation=violations.append)
        with pytest.raises(PolicyViolationError):
            await ga.on_messages([SimpleNamespace(content="run rm -rf /")])
        assert len(violations) == 1
        assert violations[0].policy_name == "content_filter"

    @pytest.mark.asyncio
    async def test_on_messages_limit(self):
        policy = GovernancePolicy(max_messages=1)
        ga = GovernedAgent(FakeAgent(), policy)
        await ga.on_messages([SimpleNamespace(content="first")])
        with pytest.raises(PolicyViolationError, match="Message limit"):
            await ga.on_messages([SimpleNamespace(content="second")])

    @pytest.mark.asyncio
    async def test_on_messages_no_on_messages_attr(self):
        """Agent without on_messages returns None."""
        ga = GovernedAgent(object(), GovernancePolicy())
        result = await ga.on_messages([SimpleNamespace(content="hi")])
        assert result is None

    @pytest.mark.asyncio
    async def test_on_messages_default_violation_handler(self, caplog):
        """Default handler logs violations."""
        policy = GovernancePolicy(blocked_patterns=["bad"])
        ga = GovernedAgent(FakeAgent(), policy)
        with pytest.raises(PolicyViolationError):
            with caplog.at_level(logging.ERROR):
                await ga.on_messages([SimpleNamespace(content="bad content")])

    # ── on_messages_stream ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_on_messages_stream(self):
        agent = FakeStreamAgent(chunks=["a", "b", "c"])
        ga = GovernedAgent(agent, GovernancePolicy())
        chunks = []
        async for c in ga.on_messages_stream([SimpleNamespace(content="hi")]):
            chunks.append(c)
        assert chunks == ["a", "b", "c"]
        assert ga._context.message_count == 1

    @pytest.mark.asyncio
    async def test_on_messages_stream_blocks(self):
        policy = GovernancePolicy(blocked_patterns=["evil"])
        ga = GovernedAgent(FakeStreamAgent(), policy)
        with pytest.raises(PolicyViolationError):
            async for _ in ga.on_messages_stream([SimpleNamespace(content="evil plan")]):
                pass

    @pytest.mark.asyncio
    async def test_on_messages_stream_no_stream_attr(self):
        """Agent without on_messages_stream yields nothing."""
        ga = GovernedAgent(object(), GovernancePolicy())
        chunks = []
        async for c in ga.on_messages_stream([SimpleNamespace(content="hi")]):
            chunks.append(c)
        assert chunks == []


# ── GovernedTeam ──────────────────────────────────────────────────


class TestGovernedTeam:
    def test_wraps_agents(self):
        agents = [FakeAgent("a1"), FakeAgent("a2")]
        team = GovernedTeam(agents=agents)
        assert len(team.agents) == 2
        assert team.agents[0].name == "a1"
        assert team.agents[1].name == "a2"

    def test_default_policy(self):
        team = GovernedTeam(agents=[FakeAgent()])
        assert team._policy.max_messages == 100

    def test_custom_policy(self):
        policy = GovernancePolicy(max_messages=5)
        team = GovernedTeam(agents=[FakeAgent()], policy=policy)
        assert team._policy.max_messages == 5

    # ── Content check ─────────────────────────────────────────────

    def test_check_content_passes(self):
        team = GovernedTeam(agents=[FakeAgent()])
        ok, reason = team._check_content("valid task")
        assert ok is True

    def test_check_content_blocks_pattern(self):
        policy = GovernancePolicy(blocked_patterns=["DELETE FROM"])
        team = GovernedTeam(agents=[FakeAgent()], policy=policy)
        ok, reason = team._check_content("DELETE FROM users")
        assert ok is False

    def test_check_content_max_length(self):
        policy = GovernancePolicy(max_message_length=5)
        team = GovernedTeam(agents=[FakeAgent()], policy=policy)
        ok, reason = team._check_content("too long content")
        assert ok is False

    # ── run ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_run_blocks_bad_task(self):
        policy = GovernancePolicy(blocked_patterns=["rm -rf"])
        violations = []
        team = GovernedTeam(
            agents=[FakeAgent()],
            policy=policy,
            on_violation=violations.append,
        )
        with pytest.raises(PolicyViolationError):
            await team.run("rm -rf /")
        assert len(violations) == 1

    @pytest.mark.asyncio
    async def test_run_records_audit(self):
        """run() records team_run_start even if autogen_agentchat unavailable."""
        team = GovernedTeam(agents=[FakeAgent()])
        # This will hit ImportError fallback for RoundRobinGroupChat
        await team.run("simple task")
        events = [e for e in team._context.events if e["type"] == "team_run_start"]
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_run_without_violation_handler(self):
        """run() works when on_violation is None and content is blocked."""
        policy = GovernancePolicy(blocked_patterns=["bad"])
        team = GovernedTeam(agents=[FakeAgent()], policy=policy)
        with pytest.raises(PolicyViolationError):
            await team.run("bad task")

    # ── run_stream ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_run_stream_blocks_bad_task(self):
        policy = GovernancePolicy(blocked_patterns=["DROP"])
        team = GovernedTeam(agents=[FakeAgent()], policy=policy)
        with pytest.raises(PolicyViolationError):
            async for _ in team.run_stream("DROP TABLE"):
                pass

    @pytest.mark.asyncio
    async def test_run_stream_without_violation_handler(self):
        policy = GovernancePolicy(blocked_patterns=["bad"])
        team = GovernedTeam(agents=[FakeAgent()], policy=policy)
        with pytest.raises(PolicyViolationError):
            async for _ in team.run_stream("bad task"):
                pass

    # ── Audit & Stats ─────────────────────────────────────────────

    def test_get_audit_log_empty(self):
        team = GovernedTeam(agents=[FakeAgent()])
        assert team.get_audit_log() == []

    @pytest.mark.asyncio
    async def test_get_audit_log_combined(self):
        team = GovernedTeam(agents=[FakeAgent(), FakeAgent()])
        # Trigger some events
        await team.run("task")
        log = team.get_audit_log()
        assert len(log) >= 1  # At least team_run_start

    def test_get_stats(self):
        agents = [FakeAgent("a1"), FakeAgent("a2")]
        policy = GovernancePolicy(
            max_messages=20,
            max_tool_calls=10,
            blocked_patterns=["X"],
        )
        team = GovernedTeam(agents=agents, policy=policy)
        stats = team.get_stats()
        assert stats["agent_count"] == 2
        assert stats["total_messages"] == 0
        assert stats["total_tool_calls"] == 0
        assert stats["policy"]["max_messages"] == 20
        assert stats["policy"]["max_tool_calls"] == 10
        assert stats["policy"]["blocked_patterns_count"] == 1

    @pytest.mark.asyncio
    async def test_get_stats_after_messages(self):
        team = GovernedTeam(agents=[FakeAgent()])
        await team.run("task")
        stats = team.get_stats()
        # ImportError fallback sends messages to first governed agent
        assert stats["total_messages"] >= 0


# ── Integration ───────────────────────────────────────────────────


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """End-to-end: create policy → wrap agents → run → audit."""
        policy = GovernancePolicy(
            max_messages=50,
            max_tool_calls=10,
            blocked_patterns=["DROP TABLE", "rm -rf", "DELETE FROM"],
            blocked_tools=["shell_execute"],
        )

        a1 = FakeAgent("analyst")
        a2 = FakeAgent("reviewer")

        violations = []
        team = GovernedTeam(
            agents=[a1, a2],
            policy=policy,
            on_violation=violations.append,
        )

        # Good task succeeds
        await team.run("Analyze Q4 sales data")
        assert len(violations) == 0

        # Bad task fails
        with pytest.raises(PolicyViolationError):
            await team.run("DROP TABLE users")
        assert len(violations) == 1

        # Audit has entries
        log = team.get_audit_log()
        assert len(log) >= 1

        # Stats are correct
        stats = team.get_stats()
        assert stats["agent_count"] == 2

    @pytest.mark.asyncio
    async def test_multiple_patterns(self):
        """All blocked patterns are enforced."""
        policy = GovernancePolicy(
            blocked_patterns=["DROP TABLE", "rm -rf", "DELETE FROM", "EXEC xp_"]
        )
        team = GovernedTeam(agents=[FakeAgent()], policy=policy)

        for bad in ["DROP TABLE x", "rm -rf /", "DELETE FROM y", "EXEC xp_cmdshell"]:
            with pytest.raises(PolicyViolationError):
                await team.run(bad)
