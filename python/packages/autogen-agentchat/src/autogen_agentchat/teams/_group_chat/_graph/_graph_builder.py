import warnings
from typing import Callable, Dict, Literal, Optional, Union

from autogen_agentchat.base import ChatAgent
from autogen_agentchat.messages import BaseChatMessage

from ._digraph_group_chat import DiGraph, DiGraphEdge, DiGraphNode


class DiGraphBuilder:
    """
    A fluent builder for constructing :class:`DiGraph` execution graphs used in :class:`GraphFlow`.

    .. warning::

        This is an experimental feature, and the API will change in the future releases.

    This utility provides a convenient way to programmatically build a graph of agent interactions,
    including complex execution flows such as:

    - Sequential chains
    - Parallel fan-outs
    - Conditional branching
    - Cyclic loops with safe exits

    Each node in the graph represents an agent. Edges define execution paths between agents,
    and can optionally be conditioned on message content using callable functions.

    The builder is compatible with the `Graph` runner and supports both standard and filtered agents.

    Methods:
        - add_node(agent, activation): Add an agent node to the graph.
        - add_edge(source, target, condition): Connect two nodes optionally with a condition.
        - add_conditional_edges(source, condition_to_target): Add multiple conditional edges from a source.
        - set_entry_point(agent): Define the default start node (optional).
        - build(): Generate a validated `DiGraph`.
        - get_participants(): Return the list of added agents.

    Example — Sequential Flow A → B → C:
        >>> builder = GraphBuilder()
        >>> builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
        >>> builder.add_edge(agent_a, agent_b).add_edge(agent_b, agent_c)
        >>> team = Graph(
        ...     participants=builder.get_participants(),
        ...     graph=builder.build(),
        ...     termination_condition=MaxMessageTermination(5),
        ... )

    Example — Parallel Fan-out A → (B, C):
        >>> builder = GraphBuilder()
        >>> builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
        >>> builder.add_edge(agent_a, agent_b).add_edge(agent_a, agent_c)

    Example — Conditional Branching A → B or A → C:
        >>> builder = GraphBuilder()
        >>> builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
        >>> # Add conditional edges using keyword check lambdas
        >>> builder.add_conditional_edges(agent_a, {"yes": agent_b, "no": agent_c})

    Example — Using Custom String Conditions:
        >>> builder = GraphBuilder()
        >>> builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
        >>> # Add condition strings to check in messages
        >>> builder.add_edge(agent_a, agent_b, condition="big")
        >>> builder.add_edge(agent_a, agent_c, condition="small")

    Example — Loop: A → B → A or B → C:
        >>> builder = GraphBuilder()
        >>> builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
        >>> builder.add_edge(agent_a, agent_b)
        >>> builder.add_conditional_edges(agent_b, {"loop": agent_a, "exit": agent_c})
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, DiGraphNode] = {}
        self.agents: Dict[str, ChatAgent] = {}
        self._default_start_node: Optional[str] = None

    def _get_name(self, obj: Union[str, ChatAgent]) -> str:
        return obj if isinstance(obj, str) else obj.name

    def add_node(self, agent: ChatAgent, activation: Literal["all", "any"] = "all") -> "DiGraphBuilder":
        """Add a node to the graph and register its agent."""
        name = agent.name
        if name not in self.nodes:
            self.nodes[name] = DiGraphNode(name=name, edges=[], activation=activation)
            self.agents[name] = agent
        return self

    def add_edge(
        self,
        source: Union[str, ChatAgent],
        target: Union[str, ChatAgent],
        condition: Optional[Union[str, Callable[[BaseChatMessage], bool]]] = None,
    ) -> "DiGraphBuilder":
        """Add a directed edge from source to target, optionally with a condition.

        Args:
            source: Source node (agent name or agent object)
            target: Target node (agent name or agent object)
            condition: Optional condition for edge activation.
                If string, activates when substring is found in message.
                If callable, activates when function returns True for the message.

        Returns:
            Self for method chaining

        Raises:
            ValueError: If source or target node doesn't exist in the builder
        """
        source_name = self._get_name(source)
        target_name = self._get_name(target)

        if source_name not in self.nodes:
            raise ValueError(f"Source node '{source_name}' must be added before adding an edge.")
        if target_name not in self.nodes:
            raise ValueError(f"Target node '{target_name}' must be added before adding an edge.")

        self.nodes[source_name].edges.append(DiGraphEdge(target=target_name, condition=condition))
        return self

    def add_conditional_edges(
        self, source: Union[str, ChatAgent], condition_to_target: Dict[str, Union[str, ChatAgent]]
    ) -> "DiGraphBuilder":
        """Add multiple conditional edges from a source node based on keyword checks.

        .. warning::

            This method interface will be changed in the future to support callable conditions.
            Please use `add_edge` if you need to specify custom conditions.

        Args:
            source: Source node (agent name or agent object)
            condition_to_target: Mapping from condition strings to target nodes
                Each key is a keyword that will be checked in the message content
                Each value is the target node to activate when condition is met

                For each key (keyword), a lambda will be created that checks
                if the keyword is in the message text.

        Returns:
            Self for method chaining
        """

        warnings.warn(
            "add_conditional_edges will be changed in the future to support callable conditions. "
            "For now, please use add_edge if you need to specify custom conditions.",
            DeprecationWarning,
            stacklevel=2,
        )

        for condition_keyword, target in condition_to_target.items():
            self.add_edge(source, target, condition=condition_keyword)
        return self

    def set_entry_point(self, name: Union[str, ChatAgent]) -> "DiGraphBuilder":
        """Set the default start node of the graph."""
        node_name = self._get_name(name)
        if node_name not in self.nodes:
            raise ValueError(f"Start node '{node_name}' must be added before setting as entry point.")
        self._default_start_node = node_name
        return self

    def build(self) -> DiGraph:
        """Build and validate the DiGraph."""
        graph = DiGraph(
            nodes=self.nodes,
            default_start_node=self._default_start_node,
        )
        graph.graph_validate()
        return graph

    def get_participants(self) -> list[ChatAgent]:
        """Return the list of agents in the builder, in insertion order."""
        return list(self.agents.values())
