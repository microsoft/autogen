from typing import Dict, Literal, Optional, Union, Callable, Any

from autogen_agentchat.base import ChatAgent

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
    and can optionally be conditioned on message content.

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

    Example — Conditional Branching A → B ("yes"), A → C ("no"):
        >>> builder = GraphBuilder()
        >>> builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
        >>> builder.add_conditional_edges(agent_a, {"yes": agent_b, "no": agent_c})

    Example — Loop: A → B → A ("loop"), B → C ("exit"):
        >>> builder = GraphBuilder()
        >>> builder.add_node(agent_a).add_node(agent_b).add_node(agent_c)
        >>> builder.add_edge(agent_a, agent_b)
        >>> builder.add_conditional_edges(agent_b, {"loop": agent_a, "exit": agent_c})
    
    Note:
        If you use a callable (lambda/class) as a condition, the graph cannot be serialized/deserialized.
        Only use callables for in-memory, programmatic graph construction.
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
        self, source: Union[str, ChatAgent], target: Union[str, ChatAgent], condition: Optional[Union[str, Callable[[str, Any], bool]]] = None
    ) -> "DiGraphBuilder":
        """Add a directed edge from source to target, optionally with a condition (string or callable)."""
        source_name = self._get_name(source)
        target_name = self._get_name(target)

        if source_name not in self.nodes:
            raise ValueError(f"Source node '{source_name}' must be added before adding an edge.")
        if target_name not in self.nodes:
            raise ValueError(f"Target node '{target_name}' must be added before adding an edge.")

        self.nodes[source_name].edges.append(DiGraphEdge(target=target_name, condition=condition))
        return self

    def add_conditional_edges(
        self, source: Union[str, ChatAgent], condition_to_target: Dict[Union[str, Callable[[str, Any], bool]], Union[str, ChatAgent]]
    ) -> "DiGraphBuilder":
        """Add multiple conditional edges from a source node based on condition strings or callables."""
        for condition, target in condition_to_target.items():
            self.add_edge(source, target, condition)
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
