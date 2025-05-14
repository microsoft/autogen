import asyncio
from typing import Any, AsyncGenerator, Callable, Dict, List, Sequence, Set
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from autogen_agentchat.agents import (
    AssistantAgent,
    BaseChatAgent,
    MessageFilterAgent,
    MessageFilterConfig,
    PerSourceFilter,
)
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import BaseChatMessage, ChatMessage, MessageFactory, StopMessage, TextMessage
from autogen_agentchat.messages import BaseTextChatMessage as TextChatMessage
from autogen_agentchat.teams import (
    DiGraphBuilder,
    GraphFlow,
)
from autogen_agentchat.teams._group_chat._events import (  # type: ignore[attr-defined]
    BaseAgentEvent,
    GroupChatTermination,
)
from autogen_agentchat.teams._group_chat._graph._digraph_group_chat import (
    _DIGRAPH_STOP_AGENT_NAME,  # pyright: ignore[reportPrivateUsage]
    DiGraph,
    DiGraphEdge,
    DiGraphNode,
    GraphFlowManager,
)
from autogen_core import AgentRuntime, CancellationToken, Component, SingleThreadedAgentRuntime
from autogen_ext.models.replay import ReplayChatCompletionClient
from pydantic import BaseModel


def test_create_digraph() -> None:
    """Test creating a simple directed graph."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )

    assert "A" in graph.nodes
    assert "B" in graph.nodes
    assert "C" in graph.nodes
    assert len(graph.nodes["A"].edges) == 1
    assert len(graph.nodes["B"].edges) == 1
    assert len(graph.nodes["C"].edges) == 0


def test_get_parents() -> None:
    """Test computing parent relationships."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )

    parents = graph.get_parents()
    assert parents["A"] == []
    assert parents["B"] == ["A"]
    assert parents["C"] == ["B"]


def test_get_start_nodes() -> None:
    """Test retrieving start nodes (nodes with no incoming edges)."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )

    start_nodes = graph.get_start_nodes()
    assert start_nodes == set(["A"])


def test_get_leaf_nodes() -> None:
    """Test retrieving leaf nodes (nodes with no outgoing edges)."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )

    leaf_nodes = graph.get_leaf_nodes()
    assert leaf_nodes == set(["C"])


def test_serialization() -> None:
    """Test serializing and deserializing the graph."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B", condition="trigger1")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )

    serialized = graph.model_dump_json()
    deserialized_graph = DiGraph.model_validate_json(serialized)

    assert deserialized_graph.nodes["A"].edges[0].target == "B"
    assert deserialized_graph.nodes["A"].edges[0].condition == "trigger1"
    assert deserialized_graph.nodes["B"].edges[0].target == "C"


def test_invalid_graph_no_start_node() -> None:
    """Test validation failure when there is no start node."""
    graph = DiGraph(
        nodes={
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="B")]),  # Forms a cycle
        }
    )

    start_nodes = graph.get_start_nodes()
    assert len(start_nodes) == 0  # Now it correctly fails when no start nodes exist


def test_invalid_graph_no_leaf_node() -> None:
    """Test validation failure when there is no leaf node."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="A")]),  # Circular reference
        }
    )

    leaf_nodes = graph.get_leaf_nodes()
    assert len(leaf_nodes) == 0  # No true endpoint because of cycle


def test_condition_edge_execution() -> None:
    """Test conditional edge execution support."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B", condition="TRIGGER")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )

    assert graph.nodes["A"].edges[0].condition == "TRIGGER"
    assert graph.nodes["B"].edges[0].condition is None


def test_graph_with_multiple_paths() -> None:
    """Test a graph with multiple execution paths."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B"), DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="D")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="D")]),
            "D": DiGraphNode(name="D", edges=[]),
        }
    )

    parents = graph.get_parents()
    assert parents["B"] == ["A"]
    assert parents["C"] == ["A"]
    assert parents["D"] == ["B", "C"]

    start_nodes = graph.get_start_nodes()
    assert start_nodes == set(["A"])

    leaf_nodes = graph.get_leaf_nodes()
    assert leaf_nodes == set(["D"])


def test_cycle_detection_no_cycle() -> None:
    """Test that a valid acyclic graph returns False for cycle check."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    assert not graph.has_cycles_with_exit()


def test_cycle_detection_with_exit_condition() -> None:
    """Test a graph with cycle and conditional exit passes validation."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="A", condition="exit")]),  # Cycle with condition
        }
    )
    assert graph.has_cycles_with_exit()


def test_cycle_detection_without_exit_condition() -> None:
    """Test that cycle without exit condition raises an error."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="A")]),  # Cycle without condition
            "D": DiGraphNode(name="D", edges=[DiGraphEdge(target="E")]),
            "E": DiGraphNode(name="E", edges=[]),
        }
    )
    with pytest.raises(ValueError, match="Cycle detected without exit condition: A -> B -> C -> A"):
        graph.has_cycles_with_exit()


def test_validate_graph_success() -> None:
    """Test successful validation of a valid graph."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[]),
        }
    )
    # No error should be raised
    graph.graph_validate()
    assert not graph.get_has_cycles()


def test_validate_graph_missing_start_node() -> None:
    """Test validation failure when no start node exists."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="A")]),  # Cycle
        }
    )
    with pytest.raises(ValueError, match="Graph must have at least one start node"):
        graph.graph_validate()


def test_validate_graph_missing_leaf_node() -> None:
    """Test validation failure when no leaf node exists."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="B")]),  # Cycle
        }
    )
    with pytest.raises(ValueError, match="Graph must have at least one leaf node"):
        graph.graph_validate()


def test_validate_graph_mixed_conditions() -> None:
    """Test validation failure when node has mixed conditional and unconditional edges."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B", condition="cond"), DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    with pytest.raises(ValueError, match="Node 'A' has a mix of conditional and unconditional edges"):
        graph.graph_validate()


def test_get_valid_target() -> None:
    node = DiGraphNode(
        name="A",
        edges=[DiGraphEdge(target="B", condition="approve"), DiGraphEdge(target="C", condition="reject")],
    )
    manager = GraphFlowManager.__new__(GraphFlowManager)

    assert manager._get_valid_target(node, "please approve this") == "B"  # pyright: ignore[reportPrivateUsage]
    assert manager._get_valid_target(node, "i reject this") == "C"  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(RuntimeError):
        manager._get_valid_target(node, "unknown path")  # pyright: ignore[reportPrivateUsage]


def test_is_node_ready_all_and_any() -> None:
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[], activation="all"),
        }
    )

    manager = GraphFlowManager.__new__(GraphFlowManager)
    manager._graph = graph  # pyright: ignore[reportPrivateUsage]
    manager._parents = graph.get_parents()  # pyright: ignore[reportPrivateUsage]

    # === Test "all" activation ===
    # Case 1: No parent finished
    manager._pending_execution = {"C": []}  # pyright: ignore[reportPrivateUsage]
    assert not manager._is_node_ready("C")  # pyright: ignore[reportPrivateUsage]

    # Case 2: One parent finished
    manager._pending_execution = {"C": ["A"]}  # pyright: ignore[reportPrivateUsage]
    assert not manager._is_node_ready("C")  # pyright: ignore[reportPrivateUsage]

    # Case 3: All parents finished
    manager._pending_execution = {"C": ["A", "B"]}  # pyright: ignore[reportPrivateUsage]
    assert manager._is_node_ready("C")  # pyright: ignore[reportPrivateUsage]

    # === Test "any" activation ===
    graph.nodes["C"].activation = "any"

    # Case 1: No parent finished
    manager._pending_execution = {"C": []}  # pyright: ignore[reportPrivateUsage]
    assert not manager._is_node_ready("C")  # pyright: ignore[reportPrivateUsage]

    # Case 2: One parent finished
    manager._pending_execution = {"C": ["B"]}  # pyright: ignore[reportPrivateUsage]
    assert manager._is_node_ready("C")  # pyright: ignore[reportPrivateUsage]

    # Case 3: All parents finished
    manager._pending_execution = {"C": ["A", "B"]}  # pyright: ignore[reportPrivateUsage]
    assert manager._is_node_ready("C")  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_invalid_digraph_manager_cycle_without_termination() -> None:
    """Test GraphManager raises error for cyclic graph without termination condition."""
    # Create a cyclic graph A → B → A
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="A")]),
        }
    )

    output_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination] = asyncio.Queue()

    with patch(
        "autogen_agentchat.teams._group_chat._base_group_chat_manager.BaseGroupChatManager.__init__",
        return_value=None,
    ):
        manager = GraphFlowManager.__new__(GraphFlowManager)

        with pytest.raises(ValueError, match="Graph must have at least one start node"):
            manager.__init__(  # type: ignore[misc]
                name="test_manager",
                group_topic_type="topic",
                output_topic_type="topic",
                participant_topic_types=["topic1", "topic2"],
                participant_names=["A", "B"],
                participant_descriptions=["Agent A", "Agent B"],
                output_message_queue=output_queue,
                termination_condition=None,
                max_turns=None,
                message_factory=MessageFactory(),
                graph=graph,
            )


@pytest.fixture
def digraph_manager() -> Callable[..., GraphFlowManager]:
    @patch(
        "autogen_agentchat.teams._group_chat._base_group_chat_manager.BaseGroupChatManager.__init__", return_value=None
    )
    def _create(
        _: Any,
        graph: DiGraph,
        active_nodes: Set[str] | None = None,
        thread: List[BaseAgentEvent | BaseChatMessage] | None = None,
        pending: Dict[str, List[str]] | None = None,
    ) -> GraphFlowManager:
        manager = GraphFlowManager.__new__(GraphFlowManager)
        manager._graph = graph  # pyright: ignore[reportPrivateUsage]
        manager._parents = graph.get_parents()  # pyright: ignore[reportPrivateUsage]
        manager._start_nodes = graph.get_start_nodes()  # pyright: ignore[reportPrivateUsage]
        manager._leaf_nodes = graph.get_leaf_nodes()  # pyright: ignore[reportPrivateUsage]
        manager._active_nodes = set(active_nodes or [])  # pyright: ignore[reportPrivateUsage]
        manager._active_node_count = {node: 0 for node in graph.nodes}  # pyright: ignore[reportPrivateUsage]
        manager._message_factory = MessageFactory()  # pyright: ignore[reportPrivateUsage]
        manager._message_thread = thread if thread is not None else []  # pyright: ignore[reportPrivateUsage]
        manager._pending_execution = pending if pending is not None else {node: [] for node in graph.get_start_nodes()}  # pyright: ignore[reportPrivateUsage]
        manager._name = "test_manager"  # pyright: ignore[reportPrivateUsage]
        manager._use_default_start = False  # pyright: ignore[reportPrivateUsage]
        return manager

    return _create


# -------------------- Test: Sequential Flow --------------------
@pytest.mark.asyncio
async def test_select_speakers_linear(digraph_manager: Callable[..., GraphFlowManager]) -> None:
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    message_thread = [TextChatMessage(source="A", content="done", metadata={})]
    manager = digraph_manager(graph=graph, active_nodes={"A"}, thread=message_thread, pending={"B": [], "C": []})

    result = await manager.select_speakers(manager._message_thread)  # pyright: ignore[reportPrivateUsage]
    assert result == ["B"]
    assert "B" in manager._active_nodes  # pyright: ignore[reportPrivateUsage]


# -------------------- Test: Parallel Fan-out --------------------


@pytest.mark.asyncio
async def test_select_speakers_parallel(digraph_manager: Callable[..., GraphFlowManager]) -> None:
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B"), DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    message_thread = [TextChatMessage(source="A", content="done", metadata={})]
    manager = digraph_manager(graph=graph, active_nodes={"A"}, thread=message_thread, pending={"B": [], "C": []})

    result = await manager.select_speakers(manager._message_thread)  # pyright: ignore[reportPrivateUsage]
    assert set(result) == {"B", "C"}
    assert "B" in manager._active_nodes  # pyright: ignore[reportPrivateUsage]
    assert "C" in manager._active_nodes  # pyright: ignore[reportPrivateUsage]


# -------------------- Test: Conditional Path --------------------
@pytest.mark.asyncio
async def test_select_speakers_conditional(digraph_manager: Callable[..., GraphFlowManager]) -> None:
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(
                name="A", edges=[DiGraphEdge(target="B", condition="yes"), DiGraphEdge(target="C", condition="no")]
            ),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    message_thread = [TextChatMessage(source="A", content="no", metadata={})]
    manager = digraph_manager(graph=graph, active_nodes={"A"}, thread=message_thread, pending={"B": [], "C": []})

    result = await manager.select_speakers(manager._message_thread)  # pyright: ignore[reportPrivateUsage]
    assert result == ["C"]
    assert "C" in manager._active_nodes  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_select_speakers_from_start_nodes(digraph_manager: Callable[..., GraphFlowManager]) -> None:
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[]),
            "B": DiGraphNode(name="B", edges=[]),
        }
    )
    # No prior message — both are start nodes
    manager = digraph_manager(graph=graph, active_nodes=set(), thread=[], pending={"A": [], "B": []})
    result = await manager.select_speakers([])
    assert set(result) == {"A", "B"}


@pytest.mark.asyncio
async def test_select_speakers_termination(digraph_manager: Callable[..., GraphFlowManager]) -> None:
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[]),
        }
    )

    # Create the manager and manually patch _signal_termination to track calls
    manager = digraph_manager(
        graph=graph, active_nodes={"A"}, thread=[TextChatMessage(source="A", content="done", metadata={})], pending={}
    )
    manager._signal_termination = AsyncMock()  # type: ignore[assignment]

    result = await manager.select_speakers(manager._message_thread)  # pyright: ignore[reportPrivateUsage]

    # No speakers left to run, so result should be empty
    assert result == [_DIGRAPH_STOP_AGENT_NAME]


@pytest.mark.asyncio
async def test_select_speakers_conditional_all_activation(
    digraph_manager: Callable[..., GraphFlowManager],
) -> None:
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(
                name="A", edges=[DiGraphEdge(target="B", condition="yes"), DiGraphEdge(target="C", condition="no")]
            ),
            "B": DiGraphNode(name="B", edges=[], activation="all"),
            "C": DiGraphNode(name="C", edges=[], activation="all"),
        }
    )
    message_thread = [TextChatMessage(source="A", content="no", metadata={})]
    manager = digraph_manager(graph=graph, active_nodes={"A"}, thread=message_thread, pending={"B": [], "C": []})

    result = await manager.select_speakers(manager._message_thread)  # pyright: ignore[reportPrivateUsage]
    assert result == ["C"]
    assert "C" in manager._active_nodes  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_select_speakers_conditional_any_activation(
    digraph_manager: Callable[..., GraphFlowManager],
) -> None:
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(
                name="A", edges=[DiGraphEdge(target="B", condition="yes"), DiGraphEdge(target="C", condition="no")]
            ),
            "B": DiGraphNode(name="B", edges=[], activation="any"),
            "C": DiGraphNode(name="C", edges=[], activation="any"),
        }
    )
    message_thread = [TextChatMessage(source="A", content="yes", metadata={})]
    manager = digraph_manager(graph=graph, active_nodes={"A"}, thread=message_thread, pending={"B": [], "C": []})

    result = await manager.select_speakers(manager._message_thread)  # pyright: ignore[reportPrivateUsage]
    assert result == ["B"]
    assert "B" in manager._active_nodes  # pyright: ignore[reportPrivateUsage]


class _EchoAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None
        self._total_messages = 0

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    @property
    def total_messages(self) -> int:
        return self._total_messages

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        if len(messages) > 0:
            assert isinstance(messages[0], TextMessage)
            self._last_message = messages[0].content
            self._total_messages += 1
            return Response(chat_message=TextMessage(content=messages[0].content, source=self.name))
        else:
            assert self._last_message is not None
            self._total_messages += 1
            return Response(chat_message=TextMessage(content=self._last_message, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self._last_message = None


@pytest_asyncio.fixture(params=["single_threaded", "embedded"])  # type: ignore
async def runtime(request: pytest.FixtureRequest) -> AsyncGenerator[AgentRuntime | None, None]:
    if request.param == "single_threaded":
        runtime = SingleThreadedAgentRuntime()
        runtime.start()
        yield runtime
        await runtime.stop()
    elif request.param == "embedded":
        yield None


TaskType = str | List[ChatMessage] | ChatMessage


@pytest.mark.asyncio
async def test_digraph_group_chat_sequential_execution(runtime: AgentRuntime | None) -> None:
    # Create agents A → B → C
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")

    # Define graph A → B → C
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )

    # Create team using Graph
    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    # Run the chat
    result: TaskResult = await team.run(task="Hello from User")

    assert len(result.messages) == 5
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].source == "user"
    assert result.messages[1].source == "A"
    assert result.messages[2].source == "B"
    assert result.messages[3].source == "C"
    assert result.messages[4].source == _DIGRAPH_STOP_AGENT_NAME
    assert all(isinstance(m, TextMessage) for m in result.messages[:-1])
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_digraph_group_chat_parallel_fanout(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B"), DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result: TaskResult = await team.run(task="Start")
    assert len(result.messages) == 5
    assert result.messages[0].source == "user"
    assert result.messages[1].source == "A"
    assert set(m.source for m in result.messages[2:-1]) == {"B", "C"}
    assert result.messages[-1].source == _DIGRAPH_STOP_AGENT_NAME
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_digraph_group_chat_parallel_join_all(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[], activation="all"),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result: TaskResult = await team.run(task="Go")
    assert len(result.messages) == 5
    assert result.messages[0].source == "user"
    assert set([result.messages[1].source, result.messages[2].source]) == {"A", "B"}
    assert result.messages[3].source == "C"
    assert result.messages[-1].source == _DIGRAPH_STOP_AGENT_NAME
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_digraph_group_chat_parallel_join_any(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[], activation="any"),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result: TaskResult = await team.run(task="Start")

    assert len(result.messages) == 5
    assert result.messages[0].source == "user"
    sources = [m.source for m in result.messages[1:]]

    # C must be last
    assert sources[-2] == "C"

    # A and B must both execute
    assert {"A", "B"}.issubset(set(sources))

    # One of A or B must execute before C
    index_a = sources.index("A")
    index_b = sources.index("B")
    index_c = sources.index("C")
    assert index_c > min(index_a, index_b)
    assert result.messages[-1].source == _DIGRAPH_STOP_AGENT_NAME
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_digraph_group_chat_multiple_start_nodes(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[]),
            "B": DiGraphNode(name="B", edges=[]),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result: TaskResult = await team.run(task="Start")
    assert len(result.messages) == 4
    assert result.messages[0].source == "user"
    assert set(m.source for m in result.messages[1:-1]) == {"A", "B"}
    assert result.messages[-1].source == _DIGRAPH_STOP_AGENT_NAME
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_digraph_group_chat_disconnected_graph(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")
    agent_d = _EchoAgent("D", description="Echo agent D")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="D")]),
            "D": DiGraphNode(name="D", edges=[]),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c, agent_d],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(10),
    )

    result: TaskResult = await team.run(task="Go")
    assert len(result.messages) == 6
    assert result.messages[0].source == "user"
    assert {"A", "C"} == set([result.messages[1].source, result.messages[2].source])
    assert {"B", "D"} == set([result.messages[3].source, result.messages[4].source])
    assert result.messages[-1].source == _DIGRAPH_STOP_AGENT_NAME
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_digraph_group_chat_conditional_branch(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(
                name="A", edges=[DiGraphEdge(target="B", condition="yes"), DiGraphEdge(target="C", condition="no")]
            ),
            "B": DiGraphNode(name="B", edges=[], activation="any"),
            "C": DiGraphNode(name="C", edges=[], activation="any"),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result = await team.run(task="Trigger yes")
    assert result.messages[2].source == "B"


@pytest.mark.asyncio
async def test_digraph_group_chat_loop_with_exit_condition(runtime: AgentRuntime | None) -> None:
    # Agents A and C: Echo Agents
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_c = _EchoAgent("C", description="Echo agent C")

    # Replay model client for agent B
    model_client = ReplayChatCompletionClient(
        chat_completions=[
            "loop",  # First time B will ask to loop
            "loop",  # Second time B will ask to loop
            "exit",  # Third time B will say exit
        ]
    )
    # Agent B: Assistant Agent using Replay Client
    agent_b = AssistantAgent("B", description="Decision agent B", model_client=model_client)

    # DiGraph: A → B → C (conditional back to A or terminate)
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(
                name="B", edges=[DiGraphEdge(target="C", condition="exit"), DiGraphEdge(target="A", condition="loop")]
            ),
            "C": DiGraphNode(name="C", edges=[]),
        },
        default_start_node="A",
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(20),
    )

    # Run
    result = await team.run(task="Start")

    # Assert message order
    expected_sources = [
        "user",
        "A",
        "B",  # 1st loop
        "A",
        "B",  # 2nd loop
        "A",
        "B",
        "C",
        _DIGRAPH_STOP_AGENT_NAME,
    ]

    actual_sources = [m.source for m in result.messages]

    assert actual_sources == expected_sources
    assert result.stop_reason is not None
    assert result.messages[-2].source == "C"
    assert any(m.content == "exit" for m in result.messages[:-1])  # type: ignore[attr-defined,union-attr]
    assert result.messages[-1].source == _DIGRAPH_STOP_AGENT_NAME


@pytest.mark.asyncio
async def test_digraph_group_chat_parallel_join_any_1(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")
    agent_d = _EchoAgent("D", description="Echo agent D")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B"), DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="D")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="D")]),
            "D": DiGraphNode(name="D", edges=[], activation="any"),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c, agent_d],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(10),
    )

    result = await team.run(task="Run parallel join")
    sequence = [msg.source for msg in result.messages if isinstance(msg, TextMessage)]
    assert sequence[0] == "user"
    # B and C should both run
    assert "B" in sequence
    assert "C" in sequence
    # D should trigger twice → once after B and once after C (order depends on runtime)
    d_indices = [i for i, s in enumerate(sequence) if s == "D"]
    assert len(d_indices) == 1
    # Each D trigger must be after corresponding B or C
    b_index = sequence.index("B")
    c_index = sequence.index("C")
    assert any(d > b_index for d in d_indices)
    assert any(d > c_index for d in d_indices)
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_digraph_group_chat_chained_parallel_join_any(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")
    agent_d = _EchoAgent("D", description="Echo agent D")
    agent_e = _EchoAgent("E", description="Echo agent E")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B"), DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="D")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="D")]),
            "D": DiGraphNode(name="D", edges=[DiGraphEdge(target="E")], activation="any"),
            "E": DiGraphNode(name="E", edges=[], activation="any"),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c, agent_d, agent_e],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(20),
    )

    result = await team.run(task="Run chained parallel join-any")

    sequence = [msg.source for msg in result.messages if isinstance(msg, TextMessage)]

    # D should trigger twice
    d_indices = [i for i, s in enumerate(sequence) if s == "D"]
    assert len(d_indices) == 1
    # Each D trigger must be after corresponding B or C
    b_index = sequence.index("B")
    c_index = sequence.index("C")
    assert any(d > b_index for d in d_indices)
    assert any(d > c_index for d in d_indices)

    # E should also trigger twice → once after each D
    e_indices = [i for i, s in enumerate(sequence) if s == "E"]
    assert len(e_indices) == 1
    assert e_indices[0] > d_indices[0]
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_digraph_group_chat_multiple_conditional(runtime: AgentRuntime | None) -> None:
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")
    agent_d = _EchoAgent("D", description="Echo agent D")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(
                name="A",
                edges=[
                    DiGraphEdge(target="B", condition="apple"),
                    DiGraphEdge(target="C", condition="banana"),
                    DiGraphEdge(target="D", condition="cherry"),
                ],
            ),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
            "D": DiGraphNode(name="D", edges=[]),
        }
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c, agent_d],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    # Test banana branch
    result = await team.run(task="banana")
    assert result.messages[2].source == "C"


class _TestMessageFilterAgentConfig(BaseModel):
    name: str
    description: str = "Echo test agent"


class _TestMessageFilterAgent(BaseChatAgent, Component[_TestMessageFilterAgentConfig]):
    component_config_schema = _TestMessageFilterAgentConfig
    component_provider_override = "test_group_chat_graph._TestMessageFilterAgent"

    def __init__(self, name: str, description: str = "Echo test agent") -> None:
        super().__init__(name=name, description=description)
        self.received_messages: list[BaseChatMessage] = []

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        self.received_messages.extend(messages)
        return Response(chat_message=TextMessage(content="ACK", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self.received_messages.clear()

    def _to_config(self) -> _TestMessageFilterAgentConfig:
        return _TestMessageFilterAgentConfig(name=self.name, description=self.description)

    @classmethod
    def _from_config(cls, config: _TestMessageFilterAgentConfig) -> "_TestMessageFilterAgent":
        return cls(name=config.name, description=config.description)


@pytest.mark.asyncio
async def test_message_filter_agent_empty_filter_blocks_all() -> None:
    inner_agent = _TestMessageFilterAgent("inner")
    wrapper = MessageFilterAgent(
        name="wrapper",
        wrapped_agent=inner_agent,
        filter=MessageFilterConfig(per_source=[]),
    )
    messages = [
        TextMessage(source="user", content="Hello"),
        TextMessage(source="system", content="System msg"),
    ]
    await wrapper.on_messages(messages, CancellationToken())
    assert len(inner_agent.received_messages) == 0


@pytest.mark.asyncio
async def test_message_filter_agent_with_position_none_gets_all() -> None:
    inner_agent = _TestMessageFilterAgent("inner")
    wrapper = MessageFilterAgent(
        name="wrapper",
        wrapped_agent=inner_agent,
        filter=MessageFilterConfig(per_source=[PerSourceFilter(source="user", position=None, count=None)]),
    )
    messages = [
        TextMessage(source="user", content="A"),
        TextMessage(source="user", content="B"),
        TextMessage(source="system", content="Ignore this"),
    ]
    await wrapper.on_messages(messages, CancellationToken())
    assert len(inner_agent.received_messages) == 2
    assert {m.content for m in inner_agent.received_messages} == {"A", "B"}  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_digraph_group_chat() -> None:
    inner_agent = _TestMessageFilterAgent("agent")
    wrapper = MessageFilterAgent(
        name="agent",
        wrapped_agent=inner_agent,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="last", count=2),
                PerSourceFilter(source="system", position="first", count=1),
            ]
        ),
    )
    config = wrapper.dump_component()
    loaded = MessageFilterAgent.load_component(config)
    assert loaded.name == "agent"
    assert loaded._filter == wrapper._filter  # pyright: ignore[reportPrivateUsage]
    assert loaded._wrapped_agent.name == wrapper._wrapped_agent.name  # pyright: ignore[reportPrivateUsage]

    # Run on_messages and validate filtering still works
    messages = [
        TextMessage(source="user", content="u1"),
        TextMessage(source="user", content="u2"),
        TextMessage(source="user", content="u3"),
        TextMessage(source="system", content="s1"),
        TextMessage(source="system", content="s2"),
    ]
    await loaded.on_messages(messages, CancellationToken())
    received = loaded._wrapped_agent.received_messages  # type: ignore[attr-defined]
    assert {m.content for m in received} == {"u2", "u3", "s1"}  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]


@pytest.mark.asyncio
async def test_message_filter_agent_in_digraph_group_chat(runtime: AgentRuntime | None) -> None:
    inner_agent = _TestMessageFilterAgent("filtered")
    filtered = MessageFilterAgent(
        name="filtered",
        wrapped_agent=inner_agent,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="last", count=1),
            ]
        ),
    )

    graph = DiGraph(
        nodes={
            "filtered": DiGraphNode(name="filtered", edges=[]),
        }
    )

    team = GraphFlow(
        participants=[filtered],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(3),
    )

    result = await team.run(task="only last user message matters")
    assert result.stop_reason is not None
    assert any(msg.source == "filtered" for msg in result.messages)
    assert any(msg.content == "ACK" for msg in result.messages if msg.source == "filtered")  # type: ignore[attr-defined,union-attr]


@pytest.mark.asyncio
async def test_message_filter_agent_loop_graph_visibility(runtime: AgentRuntime | None) -> None:
    agent_a_inner = _TestMessageFilterAgent("A")
    agent_a = MessageFilterAgent(
        name="A",
        wrapped_agent=agent_a_inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="first", count=1),
                PerSourceFilter(source="B", position="last", count=1),
            ]
        ),
    )

    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.replay import ReplayChatCompletionClient

    model_client = ReplayChatCompletionClient(["loop", "loop", "exit"])
    agent_b_inner = AssistantAgent("B", model_client=model_client)
    agent_b = MessageFilterAgent(
        name="B",
        wrapped_agent=agent_b_inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="first", count=1),
                PerSourceFilter(source="A", position="last", count=1),
                PerSourceFilter(source="B", position="last", count=10),
            ]
        ),
    )

    agent_c_inner = _TestMessageFilterAgent("C")
    agent_c = MessageFilterAgent(
        name="C",
        wrapped_agent=agent_c_inner,
        filter=MessageFilterConfig(
            per_source=[
                PerSourceFilter(source="user", position="first", count=1),
                PerSourceFilter(source="B", position="last", count=1),
            ]
        ),
    )

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(
                name="B",
                edges=[
                    DiGraphEdge(target="C", condition="exit"),
                    DiGraphEdge(target="A", condition="loop"),
                ],
            ),
            "C": DiGraphNode(name="C", edges=[]),
        },
        default_start_node="A",
    )

    team = GraphFlow(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(20),
    )

    result = await team.run(task="Start")
    assert result.stop_reason is not None

    # Check A received: 1 user + 2 from B
    assert [m.source for m in agent_a_inner.received_messages].count("user") == 1
    assert [m.source for m in agent_a_inner.received_messages].count("B") == 2

    # Check C received: 1 user + 1 from B
    assert [m.source for m in agent_c_inner.received_messages].count("user") == 1
    assert [m.source for m in agent_c_inner.received_messages].count("B") == 1

    # Check B received: 1 user + multiple from A + own messages
    model_msgs = await agent_b_inner.model_context.get_messages()
    sources = [m.source for m in model_msgs]  # type: ignore[union-attr]
    assert sources.count("user") == 1  # pyright: ignore[reportUnknownMemberType]
    assert sources.count("A") >= 3  # pyright: ignore[reportUnknownMemberType]
    assert sources.count("B") >= 2  # pyright: ignore[reportUnknownMemberType]


# Test Graph Builder
def test_add_node() -> None:
    client = ReplayChatCompletionClient(["response"])
    agent = AssistantAgent("A", model_client=client)
    builder = DiGraphBuilder()
    builder.add_node(agent)

    assert "A" in builder.nodes
    assert "A" in builder.agents
    assert builder.nodes["A"].activation == "all"


def test_add_edge() -> None:
    client = ReplayChatCompletionClient(["1", "2"])
    a = AssistantAgent("A", model_client=client)
    b = AssistantAgent("B", model_client=client)

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b)
    builder.add_edge(a, b)

    assert builder.nodes["A"].edges[0].target == "B"
    assert builder.nodes["A"].edges[0].condition is None


def test_add_conditional_edges() -> None:
    client = ReplayChatCompletionClient(["1", "2"])
    a = AssistantAgent("A", model_client=client)
    b = AssistantAgent("B", model_client=client)
    c = AssistantAgent("C", model_client=client)

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b).add_node(c)
    builder.add_conditional_edges(a, {"yes": b, "no": c})

    edges = builder.nodes["A"].edges
    assert len(edges) == 2
    conditions = {e.condition for e in edges}
    targets = {e.target for e in edges}
    assert conditions == {"yes", "no"}
    assert targets == {"B", "C"}


def test_set_entry_point() -> None:
    client = ReplayChatCompletionClient(["ok"])
    a = AssistantAgent("A", model_client=client)
    builder = DiGraphBuilder().add_node(a).set_entry_point(a)
    graph = builder.build()

    assert graph.default_start_node == "A"


def test_build_graph_validation() -> None:
    client = ReplayChatCompletionClient(["1", "2", "3"])
    a = AssistantAgent("A", model_client=client)
    b = AssistantAgent("B", model_client=client)
    c = AssistantAgent("C", model_client=client)

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b).add_node(c)
    builder.add_edge("A", "B").add_edge("B", "C")
    builder.set_entry_point("A")
    graph = builder.build()

    assert isinstance(graph, DiGraph)
    assert set(graph.nodes.keys()) == {"A", "B", "C"}
    assert graph.get_start_nodes() == {"A"}
    assert graph.get_leaf_nodes() == {"C"}


def test_build_fan_out() -> None:
    client = ReplayChatCompletionClient(["hi"] * 3)
    a = AssistantAgent("A", model_client=client)
    b = AssistantAgent("B", model_client=client)
    c = AssistantAgent("C", model_client=client)

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b).add_node(c)
    builder.add_edge(a, b).add_edge(a, c)
    builder.set_entry_point(a)
    graph = builder.build()

    assert graph.get_start_nodes() == {"A"}
    assert graph.get_leaf_nodes() == {"B", "C"}


def test_build_parallel_join() -> None:
    client = ReplayChatCompletionClient(["go"] * 3)
    a = AssistantAgent("A", model_client=client)
    b = AssistantAgent("B", model_client=client)
    c = AssistantAgent("C", model_client=client)

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b).add_node(c, activation="all")
    builder.add_edge(a, c).add_edge(b, c)
    builder.set_entry_point(a)
    builder.add_edge(b, c)
    builder.nodes["B"] = DiGraphNode(name="B", edges=[DiGraphEdge(target="C")])
    graph = builder.build()

    assert graph.nodes["C"].activation == "all"
    assert graph.get_leaf_nodes() == {"C"}


def test_build_conditional_loop() -> None:
    client = ReplayChatCompletionClient(["loop", "loop", "exit"])
    a = AssistantAgent("A", model_client=client)
    b = AssistantAgent("B", model_client=client)
    c = AssistantAgent("C", model_client=client)

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b).add_node(c)
    builder.add_edge(a, b)
    builder.add_conditional_edges(b, {"loop": a, "exit": c})
    builder.set_entry_point(a)
    graph = builder.build()

    assert graph.nodes["B"].edges[0].condition == "loop"
    assert graph.nodes["B"].edges[1].condition == "exit"
    assert graph.has_cycles_with_exit()


@pytest.mark.asyncio
async def test_graph_builder_sequential_execution(runtime: AgentRuntime | None) -> None:
    a = _EchoAgent("A", description="Echo A")
    b = _EchoAgent("B", description="Echo B")
    c = _EchoAgent("C", description="Echo C")

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b).add_node(c)
    builder.add_edge(a, b).add_edge(b, c)

    team = GraphFlow(
        participants=builder.get_participants(),
        graph=builder.build(),
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result = await team.run(task="Start")
    assert [m.source for m in result.messages[1:-1]] == ["A", "B", "C"]
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_graph_builder_fan_out(runtime: AgentRuntime | None) -> None:
    a = _EchoAgent("A", description="Echo A")
    b = _EchoAgent("B", description="Echo B")
    c = _EchoAgent("C", description="Echo C")

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b).add_node(c)
    builder.add_edge(a, b).add_edge(a, c)

    team = GraphFlow(
        participants=builder.get_participants(),
        graph=builder.build(),
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result = await team.run(task="Start")
    sources = [m.source for m in result.messages if isinstance(m, TextMessage)]
    assert set(sources[1:]) == {"A", "B", "C"}
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_graph_builder_conditional_execution(runtime: AgentRuntime | None) -> None:
    a = _EchoAgent("A", description="Echo A")
    b = _EchoAgent("B", description="Echo B")
    c = _EchoAgent("C", description="Echo C")

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b).add_node(c)
    builder.add_conditional_edges(a, {"yes": b, "no": c})

    team = GraphFlow(
        participants=builder.get_participants(),
        graph=builder.build(),
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result = await team.run(task="no")
    sources = [m.source for m in result.messages]
    assert "C" in sources
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_graph_builder_with_filter_agent(runtime: AgentRuntime | None) -> None:
    inner = _EchoAgent("X", description="Echo X")
    filter_agent = MessageFilterAgent(
        name="X",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=[PerSourceFilter(source="user", position="last", count=1)]),
    )

    builder = DiGraphBuilder()
    builder.add_node(filter_agent)

    team = GraphFlow(
        participants=builder.get_participants(),
        graph=builder.build(),
        runtime=runtime,
        termination_condition=MaxMessageTermination(3),
    )

    result = await team.run(task="Hello")
    assert any(m.source == "X" and m.content == "Hello" for m in result.messages)  # type: ignore[union-attr]
    assert result.stop_reason is not None


@pytest.mark.asyncio
async def test_graph_flow_serialize_deserialize() -> None:
    client_a = ReplayChatCompletionClient(list(map(str, range(10))))
    client_b = ReplayChatCompletionClient(list(map(str, range(10))))
    a = AssistantAgent("A", model_client=client_a)
    b = AssistantAgent("B", model_client=client_b)

    builder = DiGraphBuilder()
    builder.add_node(a).add_node(b)
    builder.add_edge(a, b)
    builder.set_entry_point(a)

    team = GraphFlow(
        participants=builder.get_participants(),
        graph=builder.build(),
        runtime=None,
        termination_condition=MaxMessageTermination(5),
    )

    serialized = team.dump_component()
    deserialized_team = GraphFlow.load_component(serialized)
    serialized_deserialized = deserialized_team.dump_component()

    results = await team.run(task="Start")
    de_results = await deserialized_team.run(task="Start")

    assert serialized == serialized_deserialized
    assert results == de_results
    assert results.stop_reason is not None
    assert results.stop_reason == de_results.stop_reason
    assert results.messages == de_results.messages
    assert isinstance(results.messages[0], TextMessage)
    assert results.messages[0].source == "user"
    assert results.messages[0].content == "Start"
    assert isinstance(results.messages[1], TextMessage)
    assert results.messages[1].source == "A"
    assert results.messages[1].content == "0"
    assert isinstance(results.messages[2], TextMessage)
    assert results.messages[2].source == "A"
    assert results.messages[2].content == "1"
    assert isinstance(results.messages[3], TextMessage)
    assert results.messages[3].source == "B"
    assert results.messages[3].content == "0"
    assert isinstance(results.messages[-1], StopMessage)
    assert results.messages[-1].source == _DIGRAPH_STOP_AGENT_NAME
    assert results.messages[-1].content == "Digraph execution is complete"
