from typing import Dict, List, Optional, Union
import logging

from autogen.agentchat.groupchat import Agent


def get_successor_agent_names(source_agent_name:str, allowed_speaker_order:dict) -> List[str]:
    """
    Returns a list of agent names that the source_agent_name can transition to.
    allowed_speaker_order[key] contains a list of Agent. Retrieve agent name through agent.name
    """
    return [agent.name for agent in allowed_speaker_order[source_agent_name]]

def get_predecessor_agent_names(destination_agent_name:str, allowed_speaker_order:dict) -> List[str]:
    """
    Returns a list of agent names that can transition to the destination_agent_name.
    allowed_speaker_order[key] contains a list of Agent. Retrieve agent name through agent.name
    """
    return [key for key, value in allowed_speaker_order.items() if destination_agent_name in [agent.name for agent in value]]

def has_self_loops(allowed_speaker_order:dict) -> bool:
    """
    Returns True if there are self loops in the allowed_speaker_order_dict.
    """
    return any([key in [agent.name for agent in value] for key, value in allowed_speaker_order.items()])
    

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
        4. Check for contradiction between allow_repeat_speaker and allowed_speaker_order_dict

        Warnings
        1. Warning if there are isolated agent nodes
        2. Warning if the set of agents in allowed_speaker_order do not match agents
    """

    ### Errors

    # Check 1. The dictionary must have a structure of keys and list as values
    if not isinstance(allowed_speaker_order_dict, dict):
        raise ValueError("allowed_speaker_order_dict must be a dictionary.")

    # All values must be lists of Agent or empty
    if not all([isinstance(value, list) or value == [] for value in allowed_speaker_order_dict.values()]):
        raise ValueError("allowed_speaker_order_dict must be a dictionary of keys and list as values.")

    # Check 2. Every key exists in agents
    if not all([key in [agent.name for agent in agents] for key in allowed_speaker_order_dict.keys()]):
        raise ValueError("allowed_speaker_order_dict has keys not in agents' names.")

    # Check 3. Every value is a list of Agents or empty list (not string).
    if not all([all([isinstance(agent, Agent) for agent in value]) for value in allowed_speaker_order_dict.values()]):
        raise ValueError("allowed_speaker_order_dict has values that are not lists of Agents.")

    # Check 4. Check for contradiction between allow_repeat_speaker and allowed_speaker_order_dict
    if allow_repeat_speaker is False:
        offending_agents = [
                key for key, value in allowed_speaker_order_dict.items() if key in value
            ]
        if len(offending_agents) > 0:
            raise ValueError(
                f"""allowed_speaker_order_dict has self-loops when allow_repeat_speaker is set to false. Offending agents: {offending_agents}"""
            )
    elif allow_repeat_speaker is True:
        # Iterate through the keys
        # For each key, extract the list of names from value which is a List[Agent]
        # Check if the key is in the list of names
        has_self_loops = [
            key for key, value in allowed_speaker_order_dict.items() if key in [agent.name for agent in value]
        ]
        
        if len(has_self_loops) == 0:
            raise ValueError(
                f"""allowed_speaker_order_dict has no self-loops when allow_repeat_speaker is set to true."""
            )
        

    elif isinstance(allow_repeat_speaker, list):
        # First extract the names of the agents that are having self loop in allowed_speaker_order_dict
        # To do that, we iterate across all keys, and find all keys that are in their value, value is a list of Agent.
        # Need to access name from Agent.name
        self_loop_agents = [
            key for key, value in allowed_speaker_order_dict.items() if key in [agent.name for agent in value]
        ]

        # Extract the names of the agents that are allowed to repeat in allow_repeat_speaker
        allow_repeat_speaker_names = [agent.name for agent in allow_repeat_speaker]

        # Check if all of the agents in self_loop_agents are in allow_repeat_speaker and vice-versa
        # Full anti-join, aka symmetric diff
        full_anti_join = set(self_loop_agents).symmetric_difference(set(allow_repeat_speaker_names))
        if len(full_anti_join) > 0:
            raise ValueError(
                f"""allowed_speaker_order_dict has self-loops not mentioned in the list of agents allowed to repeat in allow_repeat_speaker_names. allow_repeat_speaker_names: {allow_repeat_speaker_names}; self_loop_agents: {self_loop_agents}
                """
            )


    # Warnings
    # Warning 1. Warning if there are isolated agent nodes, there are not incoming nor outgoing edges
    # Concat keys if len(value) is positive
    # Use get_successor_agent_names to get all agents that the agent can transition to
    has_outgoing_edge = []
    for key in allowed_speaker_order_dict.keys():
        if len(get_successor_agent_names(key, allowed_speaker_order_dict)) > 0:
            has_outgoing_edge.append(key)
    no_outgoing_edges = [agent.name for agent in agents if agent.name not in has_outgoing_edge]

    # allowed_speaker_order_dict.values() is a list of list of Agents
    # values_all_agents is a list of all agents in allowed_speaker_order_dict.values()
    # Use get_predecessor_agent_names to get all agents that can transition to the agent
    has_incoming_edge = []
    for agent_list in allowed_speaker_order_dict.values():
        if len(agent_list) > 0:
            has_incoming_edge.extend([agent.name for agent in agent_list])

            
    no_incoming_edges = [agent.name for agent in agents if agent.name not in has_incoming_edge]

    isolated_agents = set(no_incoming_edges).intersection(set(no_outgoing_edges))
    if len(isolated_agents) > 0:
        logging.warning(
            f"""Warning: There are isolated agent nodes, there are not incoming nor outgoing edges. Isolated agents: {isolated_agents}"""
        )

    # Warning 2. Warning if the set of agents in allowed_speaker_order do not match agents
    # Get set of agents
    agents_in_allowed_speaker_order = set(has_incoming_edge).union(set(has_outgoing_edge))
    agents_names = [agent.name for agent in agents]
    full_anti_join = set(agents_in_allowed_speaker_order).symmetric_difference(set(agents_names))
    if len(full_anti_join) > 0:
        logging.warning(
            f"""Warning: The set of agents in allowed_speaker_order do not match agents. Offending agents: {full_anti_join}"""
        )

    



def invert_disallowed_to_allowed(disallowed_speaker_order_dict: dict, agents: List[Agent]) -> dict:
    """
    Start with a fully connected allowed_speaker_order_dict of all agents. Remove edges from the fully connected allowed_speaker_order_dict according to the disallowed_speaker_order_dict to form the allowed_speaker_order_dict.
    """
    # Create a fully connected allowed_speaker_order_dict of all agents
    allowed_speaker_order_dict = {agent.name: [other_agent for other_agent in agents] for agent in agents}

    # Remove edges from allowed_speaker_order_dict according to the disallowed_speaker_order_dict
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
