#!/usr/bin/env python
"""
agentchat_behavioral_monitor — monitor vocabulary drift across AgentChat runs.

This sample uses the public AgentChat surface end to end:

- `AssistantAgent.run()` for stateful repeated turns
- `TaskResult.messages` as the observed output surface
- `ReplayChatCompletionClient` for a deterministic, runnable demo

The replay model intentionally shifts away from earlier task vocabulary over
three runs so the monitor can flag drift without relying on a live provider.
In real deployments, replace the replay model with a production model client
and keep the same monitoring pattern.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_ext.models.replay import ReplayChatCompletionClient


GHOST_LEXICON: List[str] = [
    "jwt",
    "oauth",
    "token",
    "bearer",
    "api_key",
    "secret",
    "credential",
    "bcrypt",
    "hash",
    "salt",
    "certificate",
    "tls",
    "ssl",
    "database",
    "schema",
    "migration",
    "index",
    "foreign_key",
    "transaction",
    "redis",
    "postgres",
    "sqlite",
    "mongo",
    "vector",
    "memory",
    "context",
    "retrieval",
    "embedding",
    "chunk",
    "summarize",
    "tool_call",
    "function_call",
    "handoff",
    "termination",
    "deploy",
    "container",
    "docker",
    "kubernetes",
    "endpoint",
    "webhook",
    "rate_limit",
    "timeout",
    "retry",
]

_MIN_WORD_LEN = 4
_BASELINE_FRAC = 0.25
_CURRENT_FRAC = 0.25


def _tokenize(text: str) -> Counter:
    words = re.findall(r"[a-z_]{%d,}" % _MIN_WORD_LEN, text.lower())
    return Counter(words)


def _extract_content(msg: Any) -> str:
    """Extract text from common AgentChat message shapes."""
    if isinstance(msg, TextMessage):
        return str(msg.content or "")
    if isinstance(msg, dict):
        return str(msg.get("content", "") or "")
    content = getattr(msg, "content", None)
    if isinstance(content, list):
        return " ".join(str(part) for part in content)
    if content is not None:
        return str(content)
    return str(msg)


def _tracked_messages(task_result: TaskResult) -> List[BaseAgentEvent | BaseChatMessage]:
    """Keep only textual messages that reflect agent output."""
    tracked: List[BaseAgentEvent | BaseChatMessage] = []
    for message in task_result.messages:
        if isinstance(message, TextMessage):
            tracked.append(message)
    return tracked


class BehavioralMonitor:
    """
    Stateless consistency checker for AgentChat histories.

    Computes Ghost Consistency Score (CCS) — the fraction of vocabulary from
    the baseline window (earliest turns) still present in the current window
    (latest turns). A score below `ccs_threshold` indicates that important
    task vocabulary may have dropped out of the assistant's outputs.
    """

    def __init__(
        self,
        ghost_lexicon: Optional[List[str]] = None,
        ccs_threshold: float = 0.40,
        min_messages: int = 3,
    ) -> None:
        self.ghost_lexicon = ghost_lexicon or GHOST_LEXICON
        self.ccs_threshold = ccs_threshold
        self.min_messages = min_messages

    def check(self, messages: Sequence[Any]) -> Dict[str, Any]:
        n = len(messages)
        result: Dict[str, Any] = {
            "drift_detected": False,
            "ccs": 1.0,
            "ghost_terms": [],
            "turn": n,
        }

        if n < self.min_messages:
            return result

        cutoff_b = max(1, int(n * _BASELINE_FRAC))
        cutoff_c = max(1, int(n * _CURRENT_FRAC))

        baseline_text = " ".join(_extract_content(m) for m in messages[:cutoff_b])
        current_text = " ".join(_extract_content(m) for m in messages[-cutoff_c:])

        baseline_vocab = _tokenize(baseline_text)
        current_vocab = _tokenize(current_text)

        if not baseline_vocab:
            return result

        shared = sum(1 for word in baseline_vocab if word in current_vocab)
        ccs = shared / len(baseline_vocab)
        ghost_terms = [
            term
            for term in self.ghost_lexicon
            if baseline_vocab.get(term, 0) > 0 and current_vocab.get(term, 0) == 0
        ]

        result["ccs"] = round(ccs, 3)
        result["ghost_terms"] = ghost_terms
        result["drift_detected"] = ccs < self.ccs_threshold or bool(ghost_terms)
        return result

    def observe_result(self, history: List[Any], task_result: TaskResult) -> Dict[str, Any]:
        history.extend(_tracked_messages(task_result))
        return self.check(history)


async def main() -> None:
    model_client = ReplayChatCompletionClient(
        [
            (
                "Use jwt validation, bcrypt password hashing, redis-backed sessions, "
                "and preserve foreign_key constraints in the auth schema."
            ),
            (
                "Keep the PATCH /profile endpoint aligned with the existing auth flow: "
                "jwt bearer tokens, bcrypt hashes, and redis session checks still apply."
            ),
            (
                "Add PATCH /profile rate limiting with 429 responses and concise "
                "input validation. Keep the implementation focused on the endpoint."
            ),
        ]
    )

    agent = AssistantAgent(
        name="behavioral_monitor_demo",
        description="Deterministic AgentChat demo for behavioral drift monitoring.",
        model_client=model_client,
        system_message=(
            "You are a careful API architect. Answer tersely and stay aligned with "
            "the running implementation context."
        ),
    )

    tasks = [
        "Design the auth stack for a profile API. Mention jwt, bcrypt, redis, and foreign_key constraints.",
        "Extend the same system with a PATCH /profile endpoint while keeping earlier auth constraints intact.",
        "Now focus only on endpoint-level rate limiting and omit earlier auth details unless absolutely necessary.",
    ]

    monitor = BehavioralMonitor(min_messages=3)
    history: List[BaseAgentEvent | BaseChatMessage] = []

    print("=== AutoGen AgentChat behavioral monitor demo ===")
    for turn, task in enumerate(tasks, start=1):
        result = await agent.run(task=task, output_task_messages=False)
        report = monitor.observe_result(history, result)
        final_message = next(
            (
                _extract_content(message)
                for message in reversed(result.messages)
                if isinstance(message, TextMessage)
            ),
            "",
        )

        print(f"\nTurn {turn}")
        print(f"Task: {task}")
        print(f"Assistant: {final_message}")
        print(f"CCS: {report['ccs']}")
        print(f"Ghost terms: {report['ghost_terms']}")
        print(f"Drift detected: {report['drift_detected']}")

    print("\nInterpretation: the sample uses real AgentChat runs with a replay model.")
    print("Swap in a production model client to monitor live long-running conversations")
    print("through the same `TaskResult.messages`-based path.")


if __name__ == "__main__":
    asyncio.run(main())
