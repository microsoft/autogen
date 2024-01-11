from typing import Dict, List, Optional, Union
import logging

from autogen.agentchat.groupchat import Agent


def check_graph_validity(
    allowed_speaker_order_dict: dict,
    agents: List[Agent],
    allow_repeat_speaker: Optional[Union[bool, List[Agent]]] = True,
):
    """
    allowed_speaker_order_dict: A dictionary of keys and list as values. The keys are the names of the agents, and the values are the names of the agents that the key agent can transition to.
    agents: A list of Agents
    allow_repeat_speaker: A boolean indicating whether the same agent can speak twice in a row.

    Checks for the following:
        Errors
        1. The dictionary must have a structure of keys and list as values
        2. Every key exists in agents' names.
        3. Every value is a list of Agents (not string).
        4. The graph has at least one node
        5. The graph has at least one edge
        6. If self.allow_repeat_speaker is False, then the graph has no self-loops

        Warnings
        1. Warning if there are isolated agent nodes
        2. Warning if there are any agents in self.agents not in graph
    """

    ### Errors

    # Check 1. The dictionary must have a structure of keys and list as values
    if not isinstance(allowed_speaker_order_dict, dict):
        raise ValueError("The graph must be a dictionary.")

    # All values must be lists of Agent or empty
    if not all([isinstance(value, list) or value == [] for value in allowed_speaker_order_dict.values()]):
        raise ValueError("The graph must be a dictionary of keys and list as values.")

    # Check 2. Every key exists in agents
    if not all([key in [agent.name for agent in agents] for key in allowed_speaker_order_dict.keys()]):
        raise ValueError("The graph has keys not in agents' names.")

    # Check 3. Every value is a list of Agents or empty list (not string).
    if not all([all([isinstance(agent, Agent) for agent in value]) for value in allowed_speaker_order_dict.values()]):
        raise ValueError("The graph has values that are not lists of Agents.")

    # Check 4. The graph has at least one node
    if len(allowed_speaker_order_dict.keys()) == 0:
        raise ValueError("The graph has no nodes.")

    # Check 5. The graph has at least one edge
    if len(sum(allowed_speaker_order_dict.values(), [])) == 0:
        raise ValueError("The graph has no edges.")

    # Check 6. If self.allow_repeat_speaker is False, then the graph has no self-loops
    if allow_repeat_speaker is False:
        if any([key in value for key, value in allowed_speaker_order_dict.items()]):
            raise ValueError("The graph has self-loops when allow_repeat_speaker is set to false.")
    elif isinstance(allow_repeat_speaker, list):
        # First extract the names of the agents that are having self loop in allowed_speaker_order_dict
        # To do that, we iterate across all keys, and find all keys that are in their value, value is a list of Agent.
        # Need to access name from Agent.name
        self_loop_agents = [
            key for key, value in allowed_speaker_order_dict.items() if key in [agent.name for agent in value]
        ]

        # Extract the names of the agents that are allowed to repeat in allow_repeat_speaker
        allow_repeat_speaker_names = [agent.name for agent in allow_repeat_speaker]

        # Check if all of the agents in self_loop_agents are in allow_repeat_speaker
        if not all([agent in allow_repeat_speaker_names for agent in self_loop_agents]):
            raise ValueError(
                f"""The graph (allowed_speaker_order_dict) has self-loops not mentioned in the list of agents allowed to repeat in allow_repeat_speaker_names. allow_repeat_speaker_names: {allow_repeat_speaker_names}; self_loop_agents: {self_loop_agents}
                """
            )

    # Warnings
    # Warning 1. Warning if there are isolated agent nodes
    if any([len(value) == 0 for value in allowed_speaker_order_dict.values()]):
        logging.warning("Warning: There are isolated agent nodes.")

    # Warning 2. Warning if there are any agents in self.agents not in graph
    if any([agent.name not in allowed_speaker_order_dict.keys() for agent in agents]):
        logging.warning("Warning: There are agents in self.agents not in graph.")


def invert_disallowed_to_allowed(disallowed_speaker_order_dict: dict, agents: List[Agent]) -> dict:
    """
    Start with a fully connected graph of all agents. Remove edges from the fully connected graph according to the disallowed_speaker_order_dict to form the allowed_speaker_order_dict.
    """

    # Create a fully connected graph
    # Including self loop
    allowed_speaker_order_dict = {agent.name: [other_agent for other_agent in agents] for agent in agents}

    # Remove edges from the fully connected graph according to the disallowed_speaker_order_dict
    for key, value in disallowed_speaker_order_dict.items():
        allowed_speaker_order_dict[key] = [agent for agent in allowed_speaker_order_dict[key] if agent not in value]

    return allowed_speaker_order_dict


def visualize_speaker_order_dict(speaker_order_dict: dict, agents: List[Agent]):
    """
    Visualize the speaker_order_dict using networkx.
    """
    try:
        import networkx as nx
        import matplotlib.pyplot as plt
    except ImportError as e:
        logging.fatal("Failed to import networkx or matplotlib. Try running 'pip install autogen[graphs]'")
        raise e

    G = nx.DiGraph()

    # Add nodes
    G.add_nodes_from([agent.name for agent in agents])

    # Add edges
    for key, value in speaker_order_dict.items():
        for agent in value:
            G.add_edge(key, agent.name)

    # Visualize
    nx.draw(G, with_labels=True, font_weight="bold")
    plt.show()
