import asyncio
import logging
from typing import AsyncGenerator, List, Sequence

import pytest
import pytest_asyncio
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import (
    AssistantAgent,
    BaseChatAgent,
)
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import (
    ChatMessage,
    BaseTextChatMessage as TextChatMessage,
    StopMessage,
    TextMessage,
    MessageFactory
)
from autogen_agentchat.teams._group_chat._digraph_group_chat import DiGraphGroupChat, DiGraph, DiGraphGroupChatManager, DiGraphManagerState, DiGraphNode, DiGraphEdge
from autogen_core import AgentRuntime, CancellationToken, SingleThreadedAgentRuntime
from autogen_ext.models.replay import ReplayChatCompletionClient
from pydantic import BaseModel
from utils import FileLogHandler
from unittest.mock import patch, AsyncMock

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_group_chat.log"))


def test_create_digraph():
    """Test creating a simple directed graph."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[])
        }
    )

    assert "A" in graph.nodes
    assert "B" in graph.nodes
    assert "C" in graph.nodes
    assert len(graph.nodes["A"].edges) == 1
    assert len(graph.nodes["B"].edges) == 1
    assert len(graph.nodes["C"].edges) == 0


def test_get_parents():
    """Test computing parent relationships."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[])
        }
    )

    parents = graph.get_parents()
    assert parents["A"] == []
    assert parents["B"] == ["A"]
    assert parents["C"] == ["B"]


def test_get_start_nodes():
    """Test retrieving start nodes (nodes with no incoming edges)."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[])
        }
    )

    start_nodes = graph.get_start_nodes()
    assert start_nodes == set(["A"])


def test_get_leaf_nodes():
    """Test retrieving leaf nodes (nodes with no outgoing edges)."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[])
        }
    )

    leaf_nodes = graph.get_leaf_nodes()
    assert leaf_nodes == set(["C"])


def test_serialization():
    """Test serializing and deserializing the graph."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B", condition="trigger1")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[])
        }
    )

    serialized = graph.model_dump_json()
    deserialized_graph = DiGraph.model_validate_json(serialized)

    assert deserialized_graph.nodes["A"].edges[0].target == "B"
    assert deserialized_graph.nodes["A"].edges[0].condition == "trigger1"
    assert deserialized_graph.nodes["B"].edges[0].target == "C"


def test_invalid_graph_no_start_node():
    """Test validation failure when there is no start node."""
    graph = DiGraph(
        nodes={
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="B")])  # Forms a cycle
        }
    )

    start_nodes = graph.get_start_nodes()
    assert len(start_nodes) == 0  # Now it correctly fails when no start nodes exist


def test_invalid_graph_no_leaf_node():
    """Test validation failure when there is no leaf node."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="A")])  # Circular reference
        }
    )

    leaf_nodes = graph.get_leaf_nodes()
    assert len(leaf_nodes) == 0  # No true endpoint because of cycle


def test_condition_edge_execution():
    """Test conditional edge execution support."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B", condition="TRIGGER")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[])
        }
    )

    assert graph.nodes["A"].edges[0].condition == "TRIGGER"
    assert graph.nodes["B"].edges[0].condition is None


def test_graph_with_multiple_paths():
    """Test a graph with multiple execution paths."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B"), DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="D")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="D")]),
            "D": DiGraphNode(name="D", edges=[])
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

def test_cycle_detection_no_cycle():
    """Test that a valid acyclic graph returns False for cycle check."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    assert not graph.has_cycles_with_exit()

def test_cycle_detection_with_exit_condition():
    """Test a graph with cycle and conditional exit passes validation."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="A", condition="exit")]),  # Cycle with condition
        }
    )
    assert graph.has_cycles_with_exit()


def test_cycle_detection_without_exit_condition():
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


def test_validate_graph_success():
    """Test successful validation of a valid graph."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[]),
        }
    )
    # No error should be raised
    graph.validate()
    assert not graph.get_has_cycles()


def test_validate_graph_missing_start_node():
    """Test validation failure when no start node exists."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="A")]),  # Cycle
        }
    )
    with pytest.raises(ValueError, match="Graph must have at least one start node"):
        graph.validate()


def test_validate_graph_missing_leaf_node():
    """Test validation failure when no leaf node exists."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[DiGraphEdge(target="B")]),  # Cycle
        }
    )
    with pytest.raises(ValueError, match="Graph must have at least one leaf node"):
        graph.validate()


def test_validate_graph_mixed_conditions():
    """Test validation failure when node has mixed conditional and unconditional edges."""
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[
                DiGraphEdge(target="B", condition="cond"),
                DiGraphEdge(target="C")
            ]),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    with pytest.raises(ValueError, match="Node 'A' has a mix of conditional and unconditional edges"):
        graph.validate()



def test_get_valid_target():
    node = DiGraphNode(
        name="A",
        edges=[DiGraphEdge(target="B", condition="approve"), DiGraphEdge(target="C", condition="reject")],
    )
    manager = DiGraphGroupChatManager.__new__(DiGraphGroupChatManager)

    assert manager._get_valid_target(node, "please approve this") == "B"
    assert manager._get_valid_target(node, "i reject this") == "C"
    with pytest.raises(RuntimeError):
        manager._get_valid_target(node, "unknown path")

def test_is_node_ready_all_and_any():
    graph = DiGraph(nodes={
        "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="C")]),
        "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
        "C": DiGraphNode(name="C", edges=[], activation="all"),
    })

    manager = DiGraphGroupChatManager.__new__(DiGraphGroupChatManager)
    manager._graph = graph
    manager._parents = graph.get_parents()

    # === Test "all" activation ===
    # Case 1: No parent finished
    manager._pending_execution = {"C": []}
    assert not manager._is_node_ready("C")

    # Case 2: One parent finished
    manager._pending_execution = {"C": ["A"]}
    assert not manager._is_node_ready("C")

    # Case 3: All parents finished
    manager._pending_execution = {"C": ["A", "B"]}
    assert manager._is_node_ready("C")

    # === Test "any" activation ===
    graph.nodes["C"].activation = "any"

    # Case 1: No parent finished
    manager._pending_execution = {"C": []}
    assert not manager._is_node_ready("C")

    # Case 2: One parent finished
    manager._pending_execution = {"C": ["B"]}
    assert manager._is_node_ready("C")

    # Case 3: All parents finished
    manager._pending_execution = {"C": ["A", "B"]}
    assert manager._is_node_ready("C")



@pytest.mark.asyncio
async def test_invalid_digraph_manager_cycle_without_termination():
    """Test DiGraphGroupChatManager raises error for cyclic graph without termination condition."""
    # Create a cyclic graph A → B → A
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="A")]),
        }
    )

    output_queue: asyncio.Queue = asyncio.Queue()

    with patch(
        "autogen_agentchat.teams._group_chat._base_group_chat_manager.BaseGroupChatManager.__init__",
        return_value=None,
    ):
        manager = DiGraphGroupChatManager.__new__(DiGraphGroupChatManager)

        with pytest.raises(ValueError, match="Graph must have at least one start node"):
            manager.__init__(
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
def digraph_manager():
    @patch("autogen_agentchat.teams._group_chat._base_group_chat_manager.BaseGroupChatManager.__init__", return_value=None)
    def _create(mock_super_init, graph, active_nodes=None, thread=None, pending=None):
        manager = DiGraphGroupChatManager.__new__(DiGraphGroupChatManager)
        manager._graph = graph
        manager._parents = graph.get_parents()
        manager._start_nodes = graph.get_start_nodes()
        manager._leaf_nodes = graph.get_leaf_nodes()
        manager._lock = asyncio.Lock()
        manager._active_nodes = set(active_nodes or [])
        manager._active_node_count = {node: 0 for node in graph.nodes}
        manager._message_factory = MessageFactory()
        manager._message_thread = thread if thread is not None else []
        manager._pending_execution = pending if pending is not None else {node: [] for node in graph.get_start_nodes()}
        manager._name = "test_manager"
        manager._use_default_start = False
        return manager

    return _create

# -------------------- Test: Sequential Flow --------------------
@pytest.mark.asyncio
async def test_select_speakers_linear(digraph_manager):
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    message_thread = [TextChatMessage(source="A", content="done", metadata={})]
    manager = digraph_manager(graph=graph, active_nodes={"A"}, thread=message_thread, pending={"B": [], "C": []})

    result = await manager.select_speakers(manager._message_thread)
    assert result == ["B"]
    assert "B" in manager._active_nodes

# -------------------- Test: Parallel Fan-out --------------------

@pytest.mark.asyncio
async def test_select_speakers_parallel(digraph_manager):
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B"), DiGraphEdge(target="C")]),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    message_thread = [TextChatMessage(source="A", content="done", metadata={})]
    manager = digraph_manager(graph=graph, active_nodes={"A"}, thread=message_thread, pending={"B": [], "C": []})

    result = await manager.select_speakers(manager._message_thread)
    assert set(result) == {"B", "C"}
    assert "B" in manager._active_nodes
    assert "C" in manager._active_nodes

# -------------------- Test: Conditional Path --------------------
@pytest.mark.asyncio
async def test_select_speakers_conditional(digraph_manager):
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[
                DiGraphEdge(target="B", condition="yes"),
                DiGraphEdge(target="C", condition="no")
            ]),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
        }
    )
    message_thread = [TextChatMessage(source="A", content="no", metadata={})]
    manager = digraph_manager(graph=graph, active_nodes={"A"}, thread=message_thread, pending={"B": [], "C": []})

    result = await manager.select_speakers(manager._message_thread)
    assert result == ["C"]
    assert "C" in manager._active_nodes

@pytest.mark.asyncio
async def test_select_speakers_from_start_nodes(digraph_manager):
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
async def test_select_speakers_termination(digraph_manager):
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[]),
        }
    )

    # Create the manager and manually patch _signal_termination to track calls
    manager = digraph_manager(
        graph=graph,
        active_nodes={"A"},
        thread=[TextChatMessage(source="A", content="done", metadata={})],
        pending={}
    )
    manager._signal_termination = AsyncMock()

    result = await manager.select_speakers(manager._message_thread)

    # No speakers left to run, so result should be empty
    assert result == []
    # # Termination should have been signaled
    manager._signal_termination.assert_awaited_once()

@pytest.mark.asyncio
async def test_select_speakers_conditional_all_activation(digraph_manager):
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(
                name="A",
                edges=[
                    DiGraphEdge(target="B", condition="yes"),
                    DiGraphEdge(target="C", condition="no")
                ]
            ),
            "B": DiGraphNode(name="B", edges=[], activation="all"),
            "C": DiGraphNode(name="C", edges=[], activation="all"),
        }
    )
    message_thread = [TextChatMessage(source="A", content="no", metadata={})]
    manager = digraph_manager(
        graph=graph,
        active_nodes={"A"},
        thread=message_thread,
        pending={"B": [], "C": []}
    )

    result = await manager.select_speakers(manager._message_thread)
    assert result == ["C"]
    assert "C" in manager._active_nodes

@pytest.mark.asyncio
async def test_select_speakers_conditional_any_activation(digraph_manager):
    graph = DiGraph(
        nodes={
            "A": DiGraphNode(
                name="A",
                edges=[
                    DiGraphEdge(target="B", condition="yes"),
                    DiGraphEdge(target="C", condition="no")
                ]
            ),
            "B": DiGraphNode(name="B", edges=[], activation="any"),
            "C": DiGraphNode(name="C", edges=[], activation="any"),
        }
    )
    message_thread = [TextChatMessage(source="A", content="yes", metadata={})]
    manager = digraph_manager(
        graph=graph,
        active_nodes={"A"},
        thread=message_thread,
        pending={"B": [], "C": []}
    )

    result = await manager.select_speakers(manager._message_thread)
    assert result == ["B"]
    assert "B" in manager._active_nodes

class _EchoAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None
        self._total_messages = 0

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage,)

    @property
    def total_messages(self) -> int:
        return self._total_messages

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
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

class _StopAgent(_EchoAgent):
    def __init__(self, name: str, description: str, *, stop_at: int = 1) -> None:
        super().__init__(name, description)
        self._count = 0
        self._stop_at = stop_at

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage, StopMessage)

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        self._count += 1
        if self._count < self._stop_at:
            return await super().on_messages(messages, cancellation_token)
        return Response(chat_message=StopMessage(content="TERMINATE", source=self.name))


def _pass_function(input: str) -> str:
    return "pass"


class _InputTask1(BaseModel):
    task: str
    data: List[str]


class _InputTask2(BaseModel):
    task: str
    data: str

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

    # Create team using DiGraphGroupChat
    team = DiGraphGroupChat(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    # Run the chat
    result: TaskResult = await team.run(task="Hello from User")

    assert len(result.messages) == 4
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].source == "user"
    assert result.messages[1].source == "A"
    assert result.messages[2].source == "B"
    assert result.messages[3].source == "C"
    assert all(isinstance(m, TextMessage) for m in result.messages)
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

    team = DiGraphGroupChat(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result: TaskResult = await team.run(task="Start")
    assert len(result.messages) == 4
    assert result.messages[0].source == "user"
    assert result.messages[1].source == "A"
    assert set(m.source for m in result.messages[2:]) == {"B", "C"}
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

    team = DiGraphGroupChat(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result: TaskResult = await team.run(task="Go")
    assert len(result.messages) == 4
    assert result.messages[0].source == "user"
    assert set([result.messages[1].source, result.messages[2].source]) == {"A", "B"}
    assert result.messages[3].source == "C"
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

    team = DiGraphGroupChat(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result: TaskResult = await team.run(task="Start")

    assert len(result.messages) == 4
    assert result.messages[0].source == "user"
    sources = [m.source for m in result.messages[1:]]

    # C must be last
    assert sources[-1] == "C"

    # A and B must both execute
    assert {"A", "B"}.issubset(set(sources))

    # One of A or B must execute before C
    index_a = sources.index("A")
    index_b = sources.index("B")
    index_c = sources.index("C")
    assert index_c > min(index_a, index_b)

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

    team = DiGraphGroupChat(
        participants=[agent_a, agent_b],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    result: TaskResult = await team.run(task="Start")
    assert len(result.messages) == 3
    assert result.messages[0].source == "user"
    assert set(m.source for m in result.messages[1:]) == {"A", "B"}
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

    team = DiGraphGroupChat(
        participants=[agent_a, agent_b, agent_c, agent_d],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(10),
    )

    result: TaskResult = await team.run(task="Go")
    assert len(result.messages) == 5
    assert result.messages[0].source == "user"
    assert {"A", "C"} == set([result.messages[1].source, result.messages[2].source])
    assert {"B", "D"} == set([result.messages[3].source, result.messages[4].source])
    assert result.stop_reason is not None

@pytest.mark.asyncio
async def test_digraph_group_chat_conditional_branch(runtime: AgentRuntime | None):
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[
                DiGraphEdge(target="B", condition="yes"),
                DiGraphEdge(target="C", condition="no")
            ]),
            "B": DiGraphNode(name="B", edges=[], activation="any"),
            "C": DiGraphNode(name="C", edges=[], activation="any"),
        }
    )

    team = DiGraphGroupChat(
        participants=[agent_a, agent_b, agent_c],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )
        
    result = await team.run(task="Trigger yes")
    assert result.messages[2].source == "B"

@pytest.mark.asyncio
async def test_digraph_group_chat_loop_with_exit_condition(runtime):
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
            "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C", condition="exit"), DiGraphEdge(target="A", condition="loop")]),
            "C": DiGraphNode(name="C", edges=[])
        },
        default_start_node="A"
    )

    team = DiGraphGroupChat(
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
        "A", "B",  # 1st loop
        "A", "B",  # 2nd loop
        "A", "B", "C"
    ]

    actual_sources = [m.source for m in result.messages]


    assert actual_sources == expected_sources
    assert result.stop_reason is not None
    assert result.messages[-1].source == "C"
    assert any(m.content == "exit" for m in result.messages)

@pytest.mark.asyncio
async def test_digraph_group_chat_parallel_join_any(runtime: AgentRuntime | None):
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

    team = DiGraphGroupChat(
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
    assert len(d_indices) == 2
    # Each D trigger must be after corresponding B or C
    b_index = sequence.index("B")
    c_index = sequence.index("C")
    assert any(d > b_index for d in d_indices)
    assert any(d > c_index for d in d_indices)
    assert result.stop_reason is not None

@pytest.mark.asyncio
async def test_digraph_group_chat_chained_parallel_join_any(runtime: AgentRuntime | None):
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

    team = DiGraphGroupChat(
        participants=[agent_a, agent_b, agent_c, agent_d, agent_e],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(20),
    )

    result = await team.run(task="Run chained parallel join-any")

    sequence = [msg.source for msg in result.messages if isinstance(msg, TextMessage)]

    # D should trigger twice
    d_indices = [i for i, s in enumerate(sequence) if s == "D"]
    assert len(d_indices) == 2
    # Each D trigger must be after corresponding B or C
    b_index = sequence.index("B")
    c_index = sequence.index("C")
    assert any(d > b_index for d in d_indices)
    assert any(d > c_index for d in d_indices)

    # E should also trigger twice → once after each D
    e_indices = [i for i, s in enumerate(sequence) if s == "E"]
    assert len(e_indices) == 2
    assert e_indices[0] > d_indices[0]
    assert e_indices[1] > d_indices[1]

    assert result.stop_reason is not None 

@pytest.mark.asyncio
async def test_digraph_group_chat_multiple_conditional(runtime: AgentRuntime | None):
    agent_a = _EchoAgent("A", description="Echo agent A")
    agent_b = _EchoAgent("B", description="Echo agent B")
    agent_c = _EchoAgent("C", description="Echo agent C")
    agent_d = _EchoAgent("D", description="Echo agent D")

    graph = DiGraph(
        nodes={
            "A": DiGraphNode(name="A", edges=[
                DiGraphEdge(target="B", condition="apple"),
                DiGraphEdge(target="C", condition="banana"),
                DiGraphEdge(target="D", condition="cherry"),
            ]),
            "B": DiGraphNode(name="B", edges=[]),
            "C": DiGraphNode(name="C", edges=[]),
            "D": DiGraphNode(name="D", edges=[]),
        }
    )

    team = DiGraphGroupChat(
        participants=[agent_a, agent_b, agent_c, agent_d],
        graph=graph,
        runtime=runtime,
        termination_condition=MaxMessageTermination(5),
    )

    # Test banana branch
    result = await team.run(task="banana")
    assert result.messages[2].source == "C"