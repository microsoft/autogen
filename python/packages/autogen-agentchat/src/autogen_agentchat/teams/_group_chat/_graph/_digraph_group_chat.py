import asyncio
from typing import Any, Callable, Dict, List, Literal, Mapping, Sequence, Set

from autogen_core import AgentRuntime, CancellationToken, Component, ComponentModel
from pydantic import BaseModel
from typing_extensions import Self

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import ChatAgent, OrTerminationCondition, Response, TerminationCondition
from autogen_agentchat.conditions import StopMessageTermination
from autogen_agentchat.messages import (
    BaseAgentEvent,
    BaseChatMessage,
    ChatMessage,
    MessageFactory,
    StopMessage,
    TextMessage,
)
from autogen_agentchat.state import BaseGroupChatManagerState
from autogen_agentchat.teams import BaseGroupChat

from ..._group_chat._base_group_chat_manager import BaseGroupChatManager
from ..._group_chat._events import GroupChatTermination

_DIGRAPH_STOP_AGENT_NAME = "DiGraphStopAgent"
_DIGRAPH_STOP_AGENT_MESSAGE = "Digraph execution is complete"


class DiGraphEdge(BaseModel):
    """Represents a directed edge in a DiGraph, with an optional execution condition."""

    target: str  # Target node name
    condition: str | None = None  # Optional execution condition (trigger-based)


class DiGraphNode(BaseModel):
    """Represents a node (agent) in the directed graph."""

    name: str  # Agent's name
    edges: List[DiGraphEdge] = []  # Outgoing edges
    activation: Literal["all", "any"] = "all"


class DiGraph(BaseModel):
    """Defines a directed graph structure with nodes and edges."""

    nodes: Dict[str, DiGraphNode]  # Node name → DiGraphNode mapping
    default_start_node: str | None = None  # Default start node name
    _has_cycles: bool | None = None  # Cyclic graph flag

    def get_parents(self) -> Dict[str, List[str]]:
        """Compute a mapping of each node to its parent nodes."""
        parents: Dict[str, List[str]] = {node: [] for node in self.nodes}
        for node in self.nodes.values():
            for edge in node.edges:
                parents[edge.target].append(node.name)
        return parents

    def get_start_nodes(self) -> Set[str]:
        """Return the nodes that have no incoming edges (entry points)."""
        if self.default_start_node:
            return {self.default_start_node}

        parents = self.get_parents()
        return set([node_name for node_name, parent_list in parents.items() if not parent_list])

    def get_leaf_nodes(self) -> Set[str]:
        """Return nodes that have no outgoing edges (final output nodes)."""
        return set([name for name, node in self.nodes.items() if not node.edges])

    def has_cycles_with_exit(self) -> bool:
        """
        Check if the graph has any cycles and validate that each cycle has at least one conditional edge.

        Returns:
            bool: True if there is at least one cycle and all cycles have an exit condition.
                False if there are no cycles.

        Raises:
            ValueError: If there is a cycle without any conditional edge.
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node_name: str) -> bool:
            visited.add(node_name)
            rec_stack.add(node_name)
            path.append(node_name)

            for edge in self.nodes[node_name].edges:
                target = edge.target
                if target not in visited:
                    if dfs(target):
                        return True
                elif target in rec_stack:
                    # Found a cycle → extract the cycle
                    cycle_start_index = path.index(target)
                    cycle_nodes = path[cycle_start_index:]
                    cycle_edges: List[DiGraphEdge] = []
                    for n in cycle_nodes:
                        cycle_edges.extend(self.nodes[n].edges)
                    if not any(edge.condition for edge in cycle_edges):
                        raise ValueError(
                            f"Cycle detected without exit condition: {' -> '.join(cycle_nodes + cycle_nodes[:1])}"
                        )
                    return True  # Found cycle, but it has an exit condition

            rec_stack.remove(node_name)
            path.pop()
            return False

        has_cycle = False
        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    has_cycle = True

        return has_cycle

    def get_has_cycles(self) -> bool:
        """Indicates if the graph has at least one cycle (with valid exit conditions)."""
        if self._has_cycles is None:
            self._has_cycles = self.has_cycles_with_exit()

        return self._has_cycles

    def graph_validate(self) -> None:
        """Validate graph structure and execution rules."""
        if not self.nodes:
            raise ValueError("Graph has no nodes.")

        if not self.get_start_nodes():
            raise ValueError("Graph must have at least one start node")

        if not self.get_leaf_nodes():
            raise ValueError("Graph must have at least one leaf node")

        # Outgoing edge condition validation (per node)
        for node in self.nodes.values():
            # Check that if a node has an outgoing conditional edge, then all outgoing edges are conditional
            has_condition = any(edge.condition for edge in node.edges)
            has_unconditioned = any(edge.condition is None for edge in node.edges)
            if has_condition and has_unconditioned:
                raise ValueError(f"Node '{node.name}' has a mix of conditional and unconditional edges.")

        self._has_cycles = self.has_cycles_with_exit()


class AGGraphManagerState(BaseGroupChatManagerState):
    """Tracks active execution state for DAG-based execution."""

    active_nodes: List[str] = []  # Currently executing nodes
    type: str = "AGGraphManagerState"


class AGGraphManager(BaseGroupChatManager):
    """Manages execution of agents using a Directed Graph execution model."""

    def __init__(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
        graph: DiGraph,
    ) -> None:
        """Initialize the graph-based execution manager."""
        super().__init__(
            name=name,
            group_topic_type=group_topic_type,
            output_topic_type=output_topic_type,
            participant_topic_types=participant_topic_types,
            participant_names=participant_names,
            participant_descriptions=participant_descriptions,
            output_message_queue=output_message_queue,
            termination_condition=termination_condition,
            max_turns=max_turns,
            message_factory=message_factory,
        )
        self._graph = graph
        self._graph.graph_validate()
        self._graph_has_cycles = self._graph.get_has_cycles()
        if self._graph_has_cycles and self._termination_condition is None and self._max_turns is None:
            raise ValueError("A termination condition is required for cyclic graphs without a maximum turn limit.")

        self._use_default_start = self._graph.default_start_node is not None
        self._default_start_executed = False
        self._start_nodes = graph.get_start_nodes()
        self._leaf_nodes = graph.get_leaf_nodes()
        self._parents = graph.get_parents()  # Parent node dependencies - helper dict to get all incoming edges
        self._active_nodes: Set[str] = set()  # Currently executing nodes
        self._active_node_count: Dict[str, int] = {
            node: 0 for node in graph.nodes
        }  # Number of times a node has been active

        # These are nodes next in line for execution as one or more of their parent nodes have started execution.
        # They execute when all their parent nodes have executed.
        # Nodes are added to this dict when at least one of their parent nodes becomes active.
        # Start nodes (no parents) are added to this dict at initialization as they are always ready to run.
        self._pending_execution: Dict[str, List[str]] = {node: [] for node in graph.get_start_nodes()}

    def _get_valid_target(self, node: DiGraphNode, content: str) -> str:
        """Check if a condition is met in the chat history."""
        for edge in node.edges:
            if edge.condition and edge.condition in content:
                return edge.target

        raise RuntimeError(f"Condition not met for node {node.name}. Content: {content}")

    def _is_node_ready(self, node_name: str) -> bool:
        """Check if a node is ready to execute based on its parent nodes.
        If activation is any then execute as soon as any parent has finished
        If activation is all then execute only when all parents have finished
        """
        node = self._graph.nodes[node_name]
        if node.activation == "any":
            return bool(self._pending_execution[node_name])
        return all(parent in self._pending_execution[node_name] for parent in self._parents[node_name])

    async def _select_speakers(self, thread: List[BaseAgentEvent | BaseChatMessage], many: bool = True) -> List[str]:
        """Select the next set of agents to execute based on DAG constraints."""
        next_speakers: Set[str] = set()
        source_node: DiGraphNode | None = None
        source: str | None = None

        if thread and isinstance(thread[-1], BaseChatMessage):
            source = thread[-1].source  # name of the agent that just finished
            content = thread[-1].to_model_text()

            # Safety check: only an active node can send a response
            if source != "user":
                if source not in self._active_nodes:
                    raise RuntimeError(f"Agent '{source}' is not currently active.")

                # Mark the node as no longer active (it just finished)
                self._active_node_count[source] -= 1

                if self._active_node_count[source] <= 0:
                    self._active_nodes.remove(source)

                source_node = self._graph.nodes[source]

                if source_node.edges:
                    # Case: conditional edges — only execute if condition is met
                    target_nodes_names: List[str] = []
                    if source_node.edges[0].condition is not None:
                        target_nodes_names = [self._get_valid_target(source_node, content)]
                        other_nodes = [
                            edge.target for edge in source_node.edges if edge.target != target_nodes_names[0]
                        ]
                        for other_node in other_nodes:
                            other_active_parents = [
                                parent
                                for parent in self._parents[other_node]
                                if (parent != source and parent in self._active_nodes)
                            ]
                            if not other_active_parents:
                                self._pending_execution.pop(other_node)
                            else:
                                self._pending_execution[other_node] = other_active_parents

                    else:
                        # Case: unconditional edges — mark this source as completed for all its children
                        target_nodes_names = [edge.target for edge in source_node.edges]

                    for target in target_nodes_names:
                        self._pending_execution[target].append(source)
            else:
                # TODO: Check if there are any usecase where the User can decide on the next speaker
                pass

        # After updating _pending_execution, check which nodes are now unblocked
        for node_name in list(self._pending_execution):
            if self._use_default_start and not self._default_start_executed:
                if node_name == self._graph.default_start_node:
                    next_speakers.add(node_name)
                    self._default_start_executed = True
                    break

            if self._is_node_ready(node_name):
                next_speakers.add(node_name)
                node = self._graph.nodes[node_name]
                if node.activation == "all":
                    self._pending_execution.pop(node_name)
                else:
                    # If activation is any, remove the parent that just finished
                    if source is not None:
                        self._pending_execution[node_name] = [
                            parent for parent in self._pending_execution[node_name] if parent != source
                        ]

                    # If none of the other parents of this node are active, remove this node from pending execution
                    node_parents = self._parents[node_name]
                    if not any(parent in self._active_nodes for parent in node_parents):
                        self._pending_execution.pop(node_name)

                if not many:
                    break

        # Prepopulate children of next_speakers into _pending_execution
        for node_name in next_speakers:
            for edge in self._graph.nodes[node_name].edges:
                if edge.target not in self._pending_execution:
                    self._pending_execution[edge.target] = []

        # Mark newly selected speakers as active
        for speaker in next_speakers:
            if speaker not in self._active_nodes:
                self._active_nodes.add(speaker)

            self._active_node_count[speaker] += 1

        if not self._pending_execution and not next_speakers and not self._active_nodes:
            next_speakers = set([_DIGRAPH_STOP_AGENT_NAME])  # Call the termination agent

        return list(next_speakers)

    async def select_speakers(self, thread: List[BaseAgentEvent | BaseChatMessage]) -> List[str]:
        return await self._select_speakers(thread)

    async def select_speaker(self, thread: List[BaseAgentEvent | BaseChatMessage]) -> str:
        """Select a speaker from the participants and return the
        topic type of the selected speaker."""
        speakers = await self._select_speakers(thread, many=False)
        if not speakers:
            raise RuntimeError("No available speakers found.")
        return speakers[0]

    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        pass

    async def save_state(self) -> Mapping[str, Any]:
        """Save the execution state."""
        state = {
            "message_thread": [message.dump() for message in self._message_thread],
            "current_turn": self._current_turn,
            "active_nodes": list(self._active_nodes),
            "pending_execution": self._pending_execution,
            "active_node_count": self._active_node_count,
            "default_start_executed": self._default_start_executed,
        }
        return state

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore execution state from saved data."""
        self._message_thread = [self._message_factory.create(msg) for msg in state["message_thread"]]
        self._current_turn = state["current_turn"]
        self._active_nodes = set(state["active_nodes"])
        self._pending_execution = state["pending_execution"]
        self._active_node_count = state["active_node_count"]
        self._default_start_executed = state.get("default_start_executed", False)

    async def reset(self) -> None:
        """Reset execution state to the start of the graph."""
        self._current_turn = 0
        self._message_thread.clear()
        if self._termination_condition:
            await self._termination_condition.reset()

        self._active_nodes = set()
        self._active_node_count = {node: 0 for node in self._graph.nodes}
        self._pending_execution = {node: [] for node in self._start_nodes}
        self._default_start_executed = False


class _StopAgent(BaseChatAgent):
    def __init__(self) -> None:
        super().__init__(_DIGRAPH_STOP_AGENT_NAME, "Agent that terminates the AGGraph.")

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage, StopMessage)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        return Response(chat_message=StopMessage(content=_DIGRAPH_STOP_AGENT_MESSAGE, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


class AGGraphConfig(BaseModel):
    """The declarative configuration for AGGraph."""

    participants: List[ComponentModel]
    termination_condition: ComponentModel | None = None
    max_turns: int | None = None
    graph: DiGraph  # The execution graph for agents


class AGGraph(BaseGroupChat, Component[AGGraphConfig]):
    """A team that runs a group chat following a Directed Graph execution pattern.

    This group chat executes agents based on a directed graph (DiGraph) structure,
    allowing complex workflows such as sequential execution, parallel fan-out,
    conditional branching, join patterns, and loops with explicit exit conditions.

    The execution order is determined by the edges defined in the `DiGraph`. Each node
    in the graph corresponds to an agent, and edges define the flow of messages between agents.
    Nodes can be configured to activate when:
        - **All** parent nodes have completed (activation="all") → default
        - **Any** parent node completes (activation="any")

    Conditional branching is supported using edge conditions, where the next agent(s) are selected
    based on content in the chat history. Loops are permitted as long as there is a condition
    that eventually exits the loop.

    Args:
        participants (List[ChatAgent]): The participants in the group chat.
        termination_condition (TerminationCondition, optional): Termination condition for the chat.
        max_turns (int, optional): Maximum number of turns before forcing termination.
        graph (DiGraph): Directed execution graph defining node flow and conditions.

    Raises:
        ValueError: If participant names are not unique, or if graph validation fails (e.g., cycles without exit).

    Examples:

    **Sequential Flow: A → B → C**

        .. code-block:: python

            async def main():
                agent_a = AssistantAgent("A", model_client=client)
                agent_b = AssistantAgent("B", model_client=client)
                agent_c = AssistantAgent("C", model_client=client)

                graph = DiGraph(
                    nodes={
                        "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
                        "B": DiGraphNode(name="B", edges=[DiGraphEdge(target="C")]),
                        "C": DiGraphNode(name="C", edges=[]),
                    }
                )

                team = AGGraph(
                    participants=[agent_a, agent_b, agent_c],
                    graph=graph,
                    termination_condition=MaxMessageTermination(5),
                )
                await team.run(task="Run sequential flow")

    **Parallel Fan-out: A → (B, C)**

        .. code-block:: python

            async def main():
                agent_a = AssistantAgent("A", model_client=client)
                agent_b = AssistantAgent("B", model_client=client)
                agent_c = AssistantAgent("C", model_client=client)

                graph = DiGraph(
                    nodes={
                        "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B"), DiGraphEdge(target="C")]),
                        "B": DiGraphNode(name="B", edges=[]),
                        "C": DiGraphNode(name="C", edges=[]),
                    }
                )

                team = AGGraph(
                    participants=[agent_a, agent_b, agent_c],
                    graph=graph,
                    termination_condition=MaxMessageTermination(5),
                )
                await team.run(task="Run parallel fan-out")

    **Conditional Branching: A → B (if 'yes') or C (if 'no')**

        .. code-block:: python

            async def main():
                agent_a = AssistantAgent("A", model_client=client)
                agent_b = AssistantAgent("B", model_client=client)
                agent_c = AssistantAgent("C", model_client=client)

                graph = DiGraph(
                    nodes={
                        "A": DiGraphNode(
                            name="A", edges=[DiGraphEdge(target="B", condition="yes"), DiGraphEdge(target="C", condition="no")]
                        ),
                        "B": DiGraphNode(name="B", edges=[]),
                        "C": DiGraphNode(name="C", edges=[]),
                    }
                )

                team = AGGraph(
                    participants=[agent_a, agent_b, agent_c],
                    graph=graph,
                    termination_condition=MaxMessageTermination(5),
                )
                await team.run(task="Should I proceed?")

    **Loop with exit condition: A → B → A (if 'loop'), B → C (if 'exit')**

        .. code-block:: python

            async def main():
                agent_a = AssistantAgent("A", model_client=client)
                agent_b = AssistantAgent("B", model_client=client)
                agent_c = AssistantAgent("C", model_client=client)

                graph = DiGraph(
                    nodes={
                        "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
                        "B": DiGraphNode(
                            name="B",
                            edges=[
                                DiGraphEdge(target="A", condition="loop"),
                                DiGraphEdge(target="C", condition="exit"),
                            ],
                        ),
                        "C": DiGraphNode(name="C", edges=[]),
                    }
                )

                team = AGGraph(
                    participants=[agent_a, agent_b, agent_c],
                    graph=graph,
                    termination_condition=MaxMessageTermination(10),
                )
                await team.run(task="Start loop")

    """

    component_config_schema = AGGraphConfig
    component_provider_override = "autogen_agentchat.teams.AGGraph"

    def __init__(
        self,
        participants: List[ChatAgent],
        graph: DiGraph,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        runtime: AgentRuntime | None = None,
        custom_message_types: List[type[BaseAgentEvent | BaseChatMessage]] | None = None,
    ) -> None:
        stop_agent = _StopAgent()
        stop_agent_termination = StopMessageTermination()
        termination_condition = (
            stop_agent_termination
            if not termination_condition
            else OrTerminationCondition(stop_agent_termination, termination_condition)
        )

        participants = [stop_agent] + participants
        super().__init__(
            participants,
            group_chat_manager_name="AGGraphManager",
            group_chat_manager_class=AGGraphManager,
            termination_condition=termination_condition,
            max_turns=max_turns,
            runtime=runtime,
            custom_message_types=custom_message_types,
        )
        self._graph = graph

    def _create_group_chat_manager_factory(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[BaseAgentEvent | BaseChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
    ) -> Callable[[], AGGraphManager]:
        """Creates the factory method for initializing the DiGraph-based chat manager."""

        def _factory() -> AGGraphManager:
            return AGGraphManager(
                name=name,
                group_topic_type=group_topic_type,
                output_topic_type=output_topic_type,
                participant_topic_types=participant_topic_types,
                participant_names=participant_names,
                participant_descriptions=participant_descriptions,
                output_message_queue=output_message_queue,
                termination_condition=termination_condition,
                max_turns=max_turns,
                message_factory=message_factory,
                graph=self._graph,
            )

        return _factory

    def _to_config(self) -> AGGraphConfig:
        """Converts the instance into a configuration object."""
        participants = [participant.dump_component() for participant in self._participants]
        termination_condition = self._termination_condition.dump_component() if self._termination_condition else None
        return AGGraphConfig(
            participants=participants,
            termination_condition=termination_condition,
            max_turns=self._max_turns,
            graph=self._graph,
        )

    @classmethod
    def _from_config(cls, config: AGGraphConfig) -> Self:
        """Reconstructs an instance from a configuration object."""
        participants = [ChatAgent.load_component(participant) for participant in config.participants]
        termination_condition = (
            TerminationCondition.load_component(config.termination_condition) if config.termination_condition else None
        )
        return cls(
            participants, graph=config.graph, termination_condition=termination_condition, max_turns=config.max_turns
        )
