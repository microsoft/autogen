# Copyright (c) Microsoft. All rights reserved.

"""
Agent-OS Governance Extension for AutoGen
==========================================

Provides kernel-level governance for AutoGen multi-agent conversations.

Features:
- Policy enforcement for agent messages
- Tool call filtering and limits
- Content pattern blocking
- Human approval workflows
- Full audit trail

Example:
    >>> from autogen_ext.governance import GovernedTeam, GovernancePolicy
    >>> from autogen_agentchat.agents import AssistantAgent
    >>>
    >>> policy = GovernancePolicy(
    ...     max_tool_calls=10,
    ...     blocked_patterns=["DROP TABLE", "rm -rf"],
    ...     require_human_approval=False,
    ... )
    >>>
    >>> team = GovernedTeam(
    ...     agents=[agent1, agent2],
    ...     policy=policy,
    ... )
    >>> result = await team.run("Analyze this data")
"""

from ._governance import (
    GovernancePolicy,
    GovernedAgent,
    GovernedTeam,
    PolicyViolationError,
    ExecutionContext,
)

__all__ = [
    "GovernancePolicy",
    "GovernedAgent",
    "GovernedTeam",
    "PolicyViolationError",
    "ExecutionContext",
]
