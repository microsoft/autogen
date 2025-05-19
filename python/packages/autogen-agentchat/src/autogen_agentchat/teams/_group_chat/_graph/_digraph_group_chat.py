import asyncio
from collections import Counter, deque
from typing import Any, Callable, Deque, Dict, List, Literal, Mapping, Sequence, Set, Union

from autogen_core import AgentRuntime, CancellationToken, Component, ComponentModel
from pydantic import BaseModel, Field, model_validator
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
    """Represents a directed edge in a :class:`DiGraph`, with an optional execution condition.

    .. warning::

        This is an experimental feature, and the API will change in the future releases.

    """

    target: str  # Target node name
    condition: Union[str, Callable[[BaseChatMessage], bool], None] = None
    """(Experimental) Condition to execute this edge.
    If None, the edge is unconditional.
    If a string, the edge is conditional on the presence of that string in the last agent chat message.
    If a callable, the edge is conditional on the callable returning True when given the last message.
    """
    
    # Using Field to exclude the condition in serialization if it's a callable
    _condition_function: Callable[[BaseChatMessage], bool] | None = Field(default=None, exclude=True)

    @model_validator(mode='after')
    def _validate_condition(self) -> 'DiGraphEdge':
        # Store callable in a separate field and set condition to a string marker
        if callable(self.condition):
            self._condition_function = self.condition
            # For serialization purposes, we'll set the condition to None
            # when storing as a pydantic model/dict
            object.__setattr__(self, 'condition', None)
        return self
    
    def check_condition(self, message: BaseChatMessage) -> bool:
        """Check if the edge condition is satisfied for the given message.
        
        Args:
            message: The message to check the condition against.
            
        Returns:
            True if condition is satisfied (None condition always returns True),
            False otherwise.
        """
        if self._condition_function is not None:
            return self._condition_function(message)
        elif isinstance(self.condition, str):
            # If it's a string, check if the string is in the message content
            return self.condition in message.to_model_text()
        return True  # None condition is always satisfied


class DiGraphNode(BaseModel):
    """Represents a node (agent) in a :class:`DiGraph`, with its outgoing edges and activation type.

    .. warning::

        This is an experimental feature, and the API will change in the future releases.

    """

    name: str  # Agent's name
    edges: List[DiGraphEdge] = []  # Outgoing edges
    activation: Literal["all", "any"] = "all"


class DiGraph(BaseModel):
    """Defines a directed graph structure with nodes and edges.
    :class:`GraphFlow` uses this to determine execution order and conditions.

    .. warning::

        This is an experimental feature, and the API will change in the future releases.

    """

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


class GraphFlowManagerState(BaseGroupChatManagerState):
    """Tracks active execution state for DAG-based execution."""

    active_nodes: List[str] = []  # Currently executing nodes
    type: str = "GraphManagerState"


class GraphFlowManager(BaseGroupChatManager):
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
        graph.graph_validate()
        if graph.get_has_cycles() and self._termination_condition is None and self._max_turns is None:
            raise ValueError("A termination condition is required for cyclic graphs without a maximum turn limit.")
        self._graph = graph
        # Lookup table for incoming edges for each node.
        self._parents = graph.get_parents()
        # Lookup table for outgoing edges for each node.
        self._edges: Dict[str, List[DiGraphEdge]] = {n: node.edges for n, node in graph.nodes.items()}
        # Activation lookup table for each node.
        self._activation: Dict[str, Literal["any", "all"]] = {n: node.activation for n, node in graph.nodes.items()}

        # === Mutable states for the graph execution ===
        # Count the number of remaining parents to activate each node.
        self._remaining: Counter[str] = Counter({n: len(p) for n, p in self._parents.items()})
        # Lookup table for nodes that have been enqueued through an any activation.
        # This is used to prevent re-adding the same node multiple times.
        self._enqueued_any: Dict[str, bool] = {n: False for n in graph.nodes}
        # Ready queue for nodes that are ready to execute, starting with the start nodes.
        self._ready: Deque[str] = deque([n for n in graph.get_start_nodes()])

    async def update_message_thread(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None:
        await super().update_message_thread(messages)

        # Find the node that ran in the current turn.
        message = messages[-1]
        if message.source not in self._graph.nodes:
            # Ignore messages from sources outside of the graph.
            return
        assert isinstance(message, BaseChatMessage)
        source = message.source
        content = message.to_model_text()

        # Propagate the update to the children of the node.
        for edge in self._edges[source]:
            # Use the new check_condition method that handles both string and callable conditions
            if not edge.check_condition(message):
                continue
            if self._activation[edge.target] == "all":
                self._remaining[edge.target] -= 1
                if self._remaining[edge.target] == 0:
                    # If all parents are done, add to the ready queue.
                    self._ready.append(edge.target)
            else:
                # If activation is any, add to the ready queue if not already enqueued.
                if not self._enqueued_any[edge.target]:
                    self._ready.append(edge.target)
                    self._enqueued_any[edge.target] = True

    async def select_speaker(self, thread: Sequence[BaseAgentEvent | BaseChatMessage]) -> List[str]:
        # Drain the ready queue for the next set of speakers.
        speakers: List[str] = []
        while self._ready:
            speaker = self._ready.popleft()
            speakers.append(speaker)
            # Reset the bookkeeping for the node that were selected.
            if self._activation[speaker] == "any":
                self._enqueued_any[speaker] = False
            else:
                self._remaining[speaker] = len(self._parents[speaker])

        # If there are no speakers, trigger the stop agent.
        if not speakers:
            speakers = [_DIGRAPH_STOP_AGENT_NAME]

        return speakers

    async def validate_group_state(self, messages: List[BaseChatMessage] | None) -> None:
        pass

    async def save_state(self) -> Mapping[str, Any]:
        """Save the execution state."""
        state = {
            "message_thread": [message.dump() for message in self._message_thread],
            "current_turn": self._current_turn,
            "remaining": dict(self._remaining),
            "enqueued_any": dict(self._enqueued_any),
            "ready": list(self._ready),
        }
        return state

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore execution state from saved data."""
        self._message_thread = [self._message_factory.create(msg) for msg in state["message_thread"]]
        self._current_turn = state["current_turn"]
        self._remaining = Counter(state["remaining"])
        self._enqueued_any = state["enqueued_any"]
        self._ready = deque(state["ready"])

    async def reset(self) -> None:
        """Reset execution state to the start of the graph."""
        self._current_turn = 0
        self._message_thread.clear()
        if self._termination_condition:
            await self._termination_condition.reset()
        self._remaining = Counter({n: len(p) for n, p in self._parents.items()})
        self._enqueued_any = {n: False for n in self._graph.nodes}
        self._ready = deque([n for n in self._graph.get_start_nodes()])


class _StopAgent(BaseChatAgent):
    def __init__(self) -> None:
        super().__init__(_DIGRAPH_STOP_AGENT_NAME, "Agent that terminates the GraphFlow.")

    @property
    def produced_message_types(self) -> Sequence[type[ChatMessage]]:
        return (TextMessage, StopMessage)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        return Response(chat_message=StopMessage(content=_DIGRAPH_STOP_AGENT_MESSAGE, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


class GraphFlowConfig(BaseModel):
    """The declarative configuration for GraphFlow."""

    participants: List[ComponentModel]
    termination_condition: ComponentModel | None = None
    max_turns: int | None = None
    graph: DiGraph  # The execution graph for agents


class GraphFlow(BaseGroupChat, Component[GraphFlowConfig]):
    """A team that runs a group chat following a Directed Graph execution pattern.

    .. warning::

        This is an experimental feature, and the API will change in the future releases.

    This group chat executes agents based on a directed graph (:class:`DiGraph`) structure,
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

    .. note::

        Use the :class:`DiGraphBuilder` class to create a :class:`DiGraph` easily. It provides a fluent API
        for adding nodes and edges, setting entry points, and validating the graph structure.
        See the :class:`DiGraphBuilder` documentation for more details.
        The :class:`GraphFlow` class is designed to be used with the :class:`DiGraphBuilder` for creating complex workflows.


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

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main():
                # Initialize agents with OpenAI model clients.
                model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
                agent_a = AssistantAgent("A", model_client=model_client, system_message="You are a helpful assistant.")
                agent_b = AssistantAgent("B", model_client=model_client, system_message="Translate input to Chinese.")
                agent_c = AssistantAgent("C", model_client=model_client, system_message="Translate input to English.")

                # Create a directed graph with sequential flow A -> B -> C.
                builder = DiGraphBuilder()
                builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
                builder.add_edge(agent_a, agent_b).add_edge(agent_b, agent_c)
                graph = builder.build()

                # Create a GraphFlow team with the directed graph.
                team = GraphFlow(
                    participants=[agent_a, agent_b, agent_c],
                    graph=graph,
                    termination_condition=MaxMessageTermination(5),
                )

                # Run the team and print the events.
                async for event in team.run_stream(task="Write a short story about a cat."):
                    print(event)


            asyncio.run(main())

        **Parallel Fan-out: A → (B, C)**

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main():
                # Initialize agents with OpenAI model clients.
                model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
                agent_a = AssistantAgent("A", model_client=model_client, system_message="You are a helpful assistant.")
                agent_b = AssistantAgent("B", model_client=model_client, system_message="Translate input to Chinese.")
                agent_c = AssistantAgent("C", model_client=model_client, system_message="Translate input to Japanese.")

                # Create a directed graph with fan-out flow A -> (B, C).
                builder = DiGraphBuilder()
                builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
                builder.add_edge(agent_a, agent_b).add_edge(agent_a, agent_c)
                graph = builder.build()

                # Create a GraphFlow team with the directed graph.
                team = GraphFlow(
                    participants=[agent_a, agent_b, agent_c],
                    graph=graph,
                    termination_condition=MaxMessageTermination(5),
                )

                # Run the team and print the events.
                async for event in team.run_stream(task="Write a short story about a cat."):
                    print(event)


            asyncio.run(main())

        **Conditional Branching: A → B (if 'yes') or C (if 'no')**

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main():
                # Initialize agents with OpenAI model clients.
                model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
                agent_a = AssistantAgent(
                    "A",
                    model_client=model_client,
                    system_message="Detect if the input is in Chinese. If it is, say 'yes', else say 'no', and nothing else.",
                )
                agent_b = AssistantAgent("B", model_client=model_client, system_message="Translate input to English.")
                agent_c = AssistantAgent("C", model_client=model_client, system_message="Translate input to Chinese.")

                # Create a directed graph with conditional branching flow A -> B ("yes"), A -> C ("no").
                builder = DiGraphBuilder()
                builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
                builder.add_edge(agent_a, agent_b, condition="yes")
                builder.add_edge(agent_a, agent_c, condition="no")
                graph = builder.build()

                # Create a GraphFlow team with the directed graph.
                team = GraphFlow(
                    participants=[agent_a, agent_b, agent_c],
                    graph=graph,
                    termination_condition=MaxMessageTermination(5),
                )

                # Run the team and print the events.
                async for event in team.run_stream(task="AutoGen is a framework for building AI agents."):
                    print(event)


            asyncio.run(main())

        **Loop with exit condition: A → B → C (if 'APPROVE') or A (if 'REJECT')**

        .. code-block:: python

            import asyncio

            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main():
                # Initialize agents with OpenAI model clients.
                model_client = OpenAIChatCompletionClient(model="gpt-4.1")
                agent_a = AssistantAgent(
                    "A",
                    model_client=model_client,
                    system_message="You are a helpful assistant.",
                )
                agent_b = AssistantAgent(
                    "B",
                    model_client=model_client,
                    system_message="Provide feedback on the input, if your feedback has been addressed, "
                    "say 'APPROVE', else say 'REJECT' and provide a reason.",
                )
                agent_c = AssistantAgent(
                    "C", model_client=model_client, system_message="Translate the final product to Korean."
                )

                # Create a loop graph with conditional exit: A -> B -> C ("APPROVE"), B -> A ("REJECT").
                builder = DiGraphBuilder()
                builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
                builder.add_edge(agent_a, agent_b)
                builder.add_conditional_edges(agent_b, {"APPROVE": agent_c, "REJECT": agent_a})
                builder.set_entry_point(agent_a)
                graph = builder.build()

                # Create a GraphFlow team with the directed graph.
                team = GraphFlow(
                    participants=[agent_a, agent_b, agent_c],
                    graph=graph,
                    termination_condition=MaxMessageTermination(20),  # Max 20 messages to avoid infinite loop.
                )

                # Run the team and print the events.
                async for event in team.run_stream(task="Write a short poem about AI Agents."):
                    print(event)


            asyncio.run(main())
    """

    component_config_schema = GraphFlowConfig
    component_provider_override = "autogen_agentchat.teams.GraphFlow"

    def __init__(
        self,
        participants: List[ChatAgent],
        graph: DiGraph,
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        runtime: AgentRuntime | None = None,
        custom_message_types: List[type[BaseAgentEvent | BaseChatMessage]] | None = None,
    ) -> None:
        self._input_participants = participants
        self._input_termination_condition = termination_condition

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
            group_chat_manager_name="GraphManager",
            group_chat_manager_class=GraphFlowManager,
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
    ) -> Callable[[], GraphFlowManager]:
        """Creates the factory method for initializing the DiGraph-based chat manager."""

        def _factory() -> GraphFlowManager:
            return GraphFlowManager(
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

    def _to_config(self) -> GraphFlowConfig:
        """Converts the instance into a configuration object."""
        participants = [participant.dump_component() for participant in self._input_participants]
        termination_condition = (
            self._input_termination_condition.dump_component() if self._input_termination_condition else None
        )
        return GraphFlowConfig(
            participants=participants,
            termination_condition=termination_condition,
            max_turns=self._max_turns,
            graph=self._graph,
        )

    @classmethod
    def _from_config(cls, config: GraphFlowConfig) -> Self:
        """Reconstructs an instance from a configuration object."""
        participants = [ChatAgent.load_component(participant) for participant in config.participants]
        termination_condition = (
            TerminationCondition.load_component(config.termination_condition) if config.termination_condition else None
        )
        return cls(
            participants, graph=config.graph, termination_condition=termination_condition, max_turns=config.max_turns
        )
