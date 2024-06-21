import logging
from typing import Dict, List, Optional

from autogen.agentchat import Agent


def has_self_loops(allowed_speaker_transitions: Dict) -> bool:
    """
    Returns True if there are self loops in the allowed_speaker_transitions_Dict.
    """
    return any([key in value for key, value in allowed_speaker_transitions.items()])


def check_graph_validity(
    allowed_speaker_transitions_dict: Dict,
    agents: List[Agent],
):
    """
    allowed_speaker_transitions_dict: A dictionary of keys and list as values. The keys are the names of the agents, and the values are the names of the agents that the key agent can transition to.
    agents: A list of Agents

    Checks for the following:
        Errors
        1. The dictionary must have a structure of keys and list as values
        2. Every key exists in agents.
        3. Every value is a list of Agents (not string).

        Warnings
        1. Warning if there are isolated agent nodes
        2. Warning if the set of agents in allowed_speaker_transitions do not match agents
        3. Warning if there are duplicated agents in any values of `allowed_speaker_transitions_dict`
    """

    ### Errors

    # Check 1. The dictionary must have a structure of keys and list as values
    if not isinstance(allowed_speaker_transitions_dict, dict):
        raise ValueError("allowed_speaker_transitions_dict must be a dictionary.")

    # All values must be lists of Agent or empty
    if not all([isinstance(value, list) for value in allowed_speaker_transitions_dict.values()]):
        raise ValueError("allowed_speaker_transitions_dict must be a dictionary with lists as values.")

    # Check 2. Every key exists in agents
    if not all([key in agents for key in allowed_speaker_transitions_dict.keys()]):
        raise ValueError("allowed_speaker_transitions_dict has keys not in agents.")

    # Check 3. Every value is a list of Agents or empty list (not string).
    if not all(
        [all([isinstance(agent, Agent) for agent in value]) for value in allowed_speaker_transitions_dict.values()]
    ):
        raise ValueError("allowed_speaker_transitions_dict has values that are not lists of Agents.")

    # Warnings
    # Warning 1. Warning if there are isolated agent nodes, there are not incoming nor outgoing edges
    # Concat keys if len(value) is positive
    has_outgoing_edge = []
    for key, agent_list in allowed_speaker_transitions_dict.items():
        if len(agent_list) > 0:
            has_outgoing_edge.append(key)
    no_outgoing_edges = [agent for agent in agents if agent not in has_outgoing_edge]

    # allowed_speaker_transitions_dict.values() is a list of list of Agents
    # values_all_agents is a list of all agents in allowed_speaker_transitions_dict.values()
    has_incoming_edge = []
    for agent_list in allowed_speaker_transitions_dict.values():
        if len(agent_list) > 0:
            has_incoming_edge.extend(agent_list)

    no_incoming_edges = [agent for agent in agents if agent not in has_incoming_edge]

    isolated_agents = set(no_incoming_edges).intersection(set(no_outgoing_edges))
    if len(isolated_agents) > 0:
        logging.warning(
            f"""Warning: There are isolated agent nodes, there are not incoming nor outgoing edges. Isolated agents: {[agent.name for agent in isolated_agents]}"""
        )

    # Warning 2. Warning if the set of agents in allowed_speaker_transitions do not match agents
    # Get set of agents
    agents_in_allowed_speaker_transitions = set(has_incoming_edge).union(set(has_outgoing_edge))
    full_anti_join = set(agents_in_allowed_speaker_transitions).symmetric_difference(set(agents))
    if len(full_anti_join) > 0:
        logging.warning(
            f"""Warning: The set of agents in allowed_speaker_transitions do not match agents. Offending agents: {[agent.name for agent in full_anti_join]}"""
        )

    # Warning 3. Warning if there are duplicated agents in any values of `allowed_speaker_transitions_dict`
    for key, values in allowed_speaker_transitions_dict.items():
        duplicates = [item for item in values if values.count(item) > 1]
        unique_duplicates = list(set(duplicates))
        if unique_duplicates:
            logging.warning(
                f"Agent '{key.name}' has duplicate elements: {[agent.name for agent in unique_duplicates]}. Please remove duplicates manually."
            )


def invert_disallowed_to_allowed(disallowed_speaker_transitions_dict: dict, agents: List[Agent]) -> dict:
    """
    Start with a fully connected allowed_speaker_transitions_dict of all agents. Remove edges from the fully connected allowed_speaker_transitions_dict according to the disallowed_speaker_transitions_dict to form the allowed_speaker_transitions_dict.
    """
    # Create a fully connected allowed_speaker_transitions_dict of all agents
    allowed_speaker_transitions_dict = {agent: [other_agent for other_agent in agents] for agent in agents}

    # Remove edges from allowed_speaker_transitions_dict according to the disallowed_speaker_transitions_dict
    for key, value in disallowed_speaker_transitions_dict.items():
        allowed_speaker_transitions_dict[key] = [
            agent for agent in allowed_speaker_transitions_dict[key] if agent not in value
        ]

    return allowed_speaker_transitions_dict


def visualize_speaker_transitions_dict(
    speaker_transitions_dict: dict, agents: List[Agent], export_path: Optional[str] = None
):
    """
    Visualize the speaker_transitions_dict using networkx.
    """
    try:
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError as e:
        logging.fatal("Failed to import networkx or matplotlib. Try running 'pip install autogen[graphs]'")
        raise e

    G = nx.DiGraph()

    # Add nodes
    G.add_nodes_from([agent.name for agent in agents])

    # Add edges
    for key, value in speaker_transitions_dict.items():
        for agent in value:
            G.add_edge(key.name, agent.name)

    # Visualize
    nx.draw(G, with_labels=True, font_weight="bold")

    if export_path is not None:
        plt.savefig(export_path)
    else:
        plt.show()
