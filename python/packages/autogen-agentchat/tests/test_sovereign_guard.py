import asyncio
import json
import os
import time
from collections import Counter, deque
from typing import Any, Dict, List, cast, Sequence, Union, AsyncGenerator

import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.teams._group_chat._graph.sovereign_guard import (
    SovereignGraphGuard,
    OperationalIschemiaError,
    IntegrityViolationError
)
from autogen_agentchat.teams._group_chat._graph._digraph_group_chat import GraphFlowManager
from autogen_core import CancellationToken
from autogen_core.models import ChatCompletionClient, CreateResult, LLMMessage, UserMessage, SystemMessage, ModelCapabilities, RequestUsage, ModelInfo
from autogen_agentchat.messages import ChatMessage

# Helper Mock Client
class MockChatCompletionClient(ChatCompletionClient):
    def __init__(self):
        pass

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] | None = None,
        json_output: bool | None = None,
        extra_create_args: Dict[str, Any] = {},
        cancellation_token: CancellationToken | None = None,
    ) -> CreateResult:
        return CreateResult(finish_reason="stop", content="Mock response", usage=RequestUsage(prompt_tokens=1, completion_tokens=1))

    def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Any] | None = None,
        json_output: bool | None = None,
        extra_create_args: Dict[str, Any] = {},
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[Any, Any]:
        async def mock_stream():
            yield "Mock"
            yield " "
            yield "Response"
        return mock_stream()

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] | None = None) -> int:
        return 1

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Any] | None = None) -> int:
        return 1000

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(vision=False, function_calling=False, json_output=False)

    def actual_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def total_usage(self) -> RequestUsage:
        return RequestUsage(prompt_tokens=0, completion_tokens=0)

    def model_info(self) -> ModelInfo:
        return ModelInfo(vision=False, function_calling=False, json_output=False, family="mock")

    def close(self):
        pass

# Helper to spy on manager
def create_test_manager(team: GraphFlow) -> GraphFlowManager:
    class MockMessageFactory:
        def create(self, msg): return msg
        @classmethod
        def get_message_type(cls): return ChatMessage

    factory = team._create_group_chat_manager_factory(
        name="TestManager",
        group_topic_type="group_topic",
        output_topic_type="output_topic",
        participant_topic_types=[f"topic_{i}" for i in range(len(team._input_participants))],
        participant_names=[p.name for p in team._input_participants],
        participant_descriptions=[p.description for p in team._input_participants],
        output_message_queue=asyncio.Queue(),
        termination_condition=team._input_termination_condition,
        max_turns=team._max_turns,
        message_factory=MockMessageFactory()
    )

    manager = factory()
    # We override it anyway
    manager._message_factory = MockMessageFactory()
    return manager

@pytest.mark.asyncio
async def test_sovereign_guard_sanity():
    """Verify basic save/load mechanics."""
    agent_a = AssistantAgent("A", model_client=MockChatCompletionClient())
    agent_b = AssistantAgent("B", model_client=MockChatCompletionClient())

    builder = DiGraphBuilder()
    builder.add_node(agent_a).add_node(agent_b)
    builder.add_edge(agent_a, agent_b)
    graph = builder.build()

    team = GraphFlow(participants=[agent_a, agent_b], graph=graph)
    manager = create_test_manager(team)

    guard = SovereignGraphGuard(manager, state_path="test_sovereign_state.json")

    try:
        # Initial State
        assert list(manager._ready) == ["A"]

        # Capture & Commit
        await guard._commit_to_disk()
        assert os.path.exists("test_sovereign_state.json")

        # Verify JSON
        with open("test_sovereign_state.json") as f:
            data = json.load(f)
            assert data["data"]["topology"]["ready"] == ["A"]

        # Simulate State Drift
        manager._ready.clear()
        assert len(manager._ready) == 0

        # Load & Heal
        guard.load_and_heal()
        assert list(manager._ready) == ["A"]

    finally:
        if os.path.exists("test_sovereign_state.json"):
            os.remove("test_sovereign_state.json")

@pytest.mark.asyncio
async def test_zombie_recovery():
    """Verify adrenaline injection for stalled graphs."""
    agent_a = AssistantAgent("A", model_client=MockChatCompletionClient())
    agent_b = AssistantAgent("B", model_client=MockChatCompletionClient())

    builder = DiGraphBuilder()
    builder.add_node(agent_a).add_node(agent_b)
    builder.add_edge(agent_a, agent_b)
    graph = builder.build()

    team = GraphFlow(participants=[agent_a, agent_b], graph=graph)
    manager = create_test_manager(team)

    guard = SovereignGraphGuard(manager, state_path="test_zombie_state.json")

    try:
        # Capture valid state first to get structure
        await guard._commit_to_disk()

        # Create a zombie state manually in the file
        with open("test_zombie_state.json", "r") as f:
            envelope = json.load(f)

        # Corrupt the state to make it a zombie
        # remaining work for B exists, but ready is empty
        envelope["data"]["topology"]["ready"] = []
        envelope["data"]["topology"]["active_nodes"] = []
        envelope["data"]["topology"]["remaining"]["B"]["A"] = 1 # Work remains

        # Update hash to prevent IntegrityViolation
        canonical = json.dumps(envelope["data"], sort_keys=True, default=str)
        import hashlib
        envelope["hash"] = hashlib.sha256(canonical.encode()).hexdigest()

        with open("test_zombie_state.json", "w") as f:
            json.dump(envelope, f)

        # Load and Heal
        guard.load_and_heal()

        # Expect B to be injected into ready
        assert list(manager._ready) == ["B"]

    finally:
        if os.path.exists("test_zombie_state.json"):
            os.remove("test_zombie_state.json")

@pytest.mark.asyncio
async def test_integrity_violation():
    """Verify hash check failure."""
    agent_a = AssistantAgent("A", model_client=MockChatCompletionClient())

    builder = DiGraphBuilder()
    builder.add_node(agent_a)
    graph = builder.build()

    team = GraphFlow(participants=[agent_a], graph=graph)
    manager = create_test_manager(team)

    guard = SovereignGraphGuard(manager, state_path="test_integrity.json")

    try:
        await guard._commit_to_disk()

        # Tamper with file CLEANLY
        with open("test_integrity.json", "r") as f:
            envelope = json.load(f)

        envelope["hash"] = "fake_hash_12345"

        with open("test_integrity.json", "w") as f:
            json.dump(envelope, f)

        with pytest.raises(IntegrityViolationError):
            guard.load_and_heal()

    finally:
        if os.path.exists("test_integrity.json"):
            os.remove("test_integrity.json")
