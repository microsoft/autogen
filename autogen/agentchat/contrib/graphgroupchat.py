import logging

try:
    import networkx as nx
    import matplotlib.pyplot as plt
except ImportError as e:
    logging.fatal("Failed to import networkx or matplotlib. Try running 'pip install autogen[graphs]'")
    raise e

import autogen
from autogen.agentchat.assistant_agent import AssistantAgent
from autogen.agentchat.groupchat import GroupChat, Agent, ConversableAgent

import random
from typing import List, Dict


class GraphGroupChat(GroupChat):
    """The GraphGroupChat class inherits from the GroupChat class, and is designed to manage a group chat where the transition paths between agents are constrained by a directed graph.
    This enables tighter control over the possible transitions between agents. Since graphs are expressive, they allow for precise control over the transitions between agents, facilitating the implementation of various organizational structures such as hierarchical, team-based, or quality review frameworks.
    - agents: a list of participating agents. Inherited from GroupChat.
    - messages: a list of messages in the group chat. Inherited from GroupChat.
    - graph: a networkx graph depicting who are the next speakers available.
    - max_round: the maximum number of rounds. Inherited from GroupChat.
    - admin_name: the name of the admin agent if there is one. Default is "Admin". Inherited from GroupChat. KeyBoardInterrupt will make the admin agent take over.
    - func_call_filter: whether to enforce function call filter. Default is True. Inherited from GroupChat.
        When set to True and when a message is a function call suggestion,
        the next speaker will be chosen from an agent which contains the corresponding function name
        in its `function_map`.
    - allow_repeat_speaker: whether to allow the same speaker to speak consecutively. Default is True. Inherited from GroupChat.
    """

    def check_graph_validity(self):
        """
        Check for the following
        1. The graph has at least one node
        2. The graph has at least one edge
        3. The graph has at least one node with 'first_round_speaker' set to True
        4. If self.allow_repeat_speaker is False, then the graph has no self-loops
        5. Warning if there are isolated agent nodes
        6. Warning if there are any agents in self.agents not in graph
        """

        # Check 1. The graph has at least one node
        if len(self.graph.nodes) == 0:
            raise ValueError("The graph has no nodes.")

        # Check 2. The graph has at least one edge
        if len(self.graph.edges) == 0:
            raise ValueError("The graph has no edges.")

        # Check 3. The graph has at least one node with 'first_round_speaker' set to True
        first_round_speakers = [
            agent
            for agent in self.agents
            if agent.name in self.graph.nodes and self.graph.nodes[agent.name].get("first_round_speaker", False)
        ]
        if not first_round_speakers:
            raise ValueError("The graph has no nodes with 'first_round_speaker' set to True.")

        # Check 4. If self.allow_repeat_speaker is False, then the graph has no self-loops
        if not self.allow_repeat_speaker and any(
            [self.graph.has_edge(agent.name, agent.name) for agent in self.agents]
        ):
            raise ValueError("The graph has self-loops, but self.allow_repeat_speaker is False.")

        # Check 5. Warning if there are isolated agent nodes
        if any([self.graph.degree(agent.name) == 0 for agent in self.agents]):
            # Name the isolated agents
            isolated_agents = [agent.name for agent in self.agents if self.graph.degree(agent.name) == 0]
            logging.warning(f"The graph has isolated agents: {isolated_agents}")

        # Check 6. Warning if there are any agents in self.agents not in graph
        if any([agent.name not in self.graph.nodes for agent in self.agents]):
            # Name the agents not in the graph
            agents_not_in_graph = [agent.name for agent in self.agents if agent.name not in self.graph.nodes]
            logging.warning(f"The graph has agents not in self.agents: {agents_not_in_graph}")

    def __init__(
        self,
        agents: List[Agent],
        messages: List[Dict],
        graph: nx.DiGraph,
        max_round: int = 10,
        admin_name: str = "Admin",
        func_call_filter: bool = True,
        allow_repeat_speaker: bool = True,
    ):
        # Inherit from GroupChat, and initialize with the given parameters (except graph)
        super().__init__(
            agents=agents,
            messages=messages,
            max_round=max_round,
            admin_name=admin_name,
            func_call_filter=func_call_filter,
            speaker_selection_method="graph",
            allow_repeat_speaker=allow_repeat_speaker,
        )

        self.previous_speaker = None  # Keep track of the previous speaker
        self.graph = graph  # The graph depicting who are the next speakers available

        # Check that the graph is a DiGraph
        if not isinstance(self.graph, nx.DiGraph):
            raise ValueError("The graph must be a networkx DiGraph.")

        # Run graph check
        self.check_graph_validity()

    # All methods are from the GroupChat class, except for select_speaker
    def select_speaker(self, last_speaker: Agent, selector: ConversableAgent) -> Agent:
        self.previous_speaker = last_speaker

        # Check if last message suggests a next speaker
        last_message = self.messages[-1] if self.messages else None
        suggested_next = None

        if last_message:
            if "NEXT:" in last_message["content"]:
                suggested_next = last_message["content"].split("NEXT: ")[-1].strip()
                # Strip full stop and comma
                suggested_next = suggested_next.replace(".", "").replace(",", "")

        # Selecting first round speaker
        if self.previous_speaker is None and self.graph is not None:
            eligible_speakers = [
                agent for agent in self.agents if self.graph.nodes[agent.name].get("first_round_speaker", False)
            ]

        # Selecting successors of the previous speaker
        elif self.previous_speaker is not None and self.graph is not None:
            eligible_speaker_names = [target for target in self.graph.successors(self.previous_speaker.name)]
            eligible_speakers = [agent for agent in self.agents if agent.name in eligible_speaker_names]

        else:
            eligible_speakers = self.agents

        # Three attempts at getting the next_speaker
        # 1. Using suggested_next if suggested_next is in the eligible_speakers.name
        # 2. Using LLM to pick from eligible_speakers, given that there is some context in self.message
        # 3. Random (catch-all)
        next_speaker = None

        if eligible_speakers:
            # 1. Using suggested_next if suggested_next is in the eligible_speakers.name
            if suggested_next in [speaker.name for speaker in eligible_speakers]:
                next_speaker = self.agent_by_name(suggested_next)

            else:
                if len(self.messages) > 1:
                    # 2. Using LLM to pick from eligible_speakers, given that there is some context in self.message
                    # auto speaker selection logic from groupchat
                    selector.update_system_message(self.select_speaker_msg(self.agents))
                    context = self.messages + [{"role": "system", "content": self.select_speaker_prompt(self.agents)}]
                    final, name = selector.generate_oai_reply(context)
                    if final:
                        if self.agent_by_name(name):
                            return self.agent_by_name(name)

                if next_speaker is None:
                    # 3. Random (catch-all)
                    next_speaker = random.choice(eligible_speakers)

            return next_speaker
        else:
            # Cannot return next_speaker with no eligible speakers
            raise ValueError("No eligible speakers found based on the graph constraints.")
