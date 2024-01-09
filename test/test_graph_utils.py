import sys
import pytest
import logging
from autogen.agentchat.groupchat import Agent
import autogen.graph_utils as gru


# Define pytest fixtures for agents and valid_graph_dict
@pytest.fixture
def agents():
    return [Agent("agent1"), Agent("agent2"), Agent("agent3")]

@pytest.fixture
def valid_graph_dict(agents):
    return {agent.name: [other_agent for other_agent in agents if other_agent != agent] for agent in agents}

# Use pytest.mark.skipif decorator for conditional skipping
@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphUtil:
    def test_valid_structure(self, agents, valid_graph_dict):
        gru.check_graph_validity(graph_dict=valid_graph_dict, agents=agents)

    def test_graph_with_invalid_structure(self, agents):
        invalid_graph_dict = {'unseen_agent': ['stranger']}
        with pytest.raises(ValueError):
            gru.check_graph_validity(invalid_graph_dict, agents)

    def test_graph_with_invalid_string(self, agents):
        invalid_graph_dict = {agent.name: ['agent1'] for agent in agents} # 'agent1' is a string, not an Agent. Therefore raises an error.
        with pytest.raises(ValueError):
            gru.check_graph_validity(invalid_graph_dict, agents)

    def test_graph_with_no_nodes(self, agents):
        empty_graph_dict = {}
        with pytest.raises(ValueError):
            gru.check_graph_validity(empty_graph_dict, agents)

    def test_graph_with_no_edges(self, agents):
        graph_dict_no_edges = {agent.name: [] for agent in agents}
        with pytest.raises(ValueError):
            gru.check_graph_validity(graph_dict_no_edges, agents)

    def test_graph_with_self_loops(self, agents):
        graph_dict_with_self_loop = {agent.name: [agent.name] for agent in agents}
        with pytest.raises(ValueError):
            gru.check_graph_validity(graph_dict_with_self_loop, agents, allow_repeat_speaker=False)

    # Test for Warning 1: Isolated agent nodes
    def test_isolated_agent_nodes_warning(self, agents, caplog):
        # Create a graph where at least one agent is isolated
        graph_dict_with_isolation = {agents[0].name: [agents[1]], agents[1].name: [agents[0]]}
        # Add an isolated agent
        graph_dict_with_isolation[agents[2].name] = []

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(graph_dict=graph_dict_with_isolation, agents=agents)
        assert "isolated agent nodes" in caplog.text

    # Test for Warning 2: Agents not in graph
    def test_agents_not_in_graph_warning(self, agents, caplog):
        # Create a graph where all but the last agent are connected in a simple chain to ensure no isolated nodes and at least one edge
        missing_agent_graph_dict = {agents[i].name: [agents[i + 1]] for i in range(len(agents) - 2)}
        # Add a connection back to the first agent to close the chain and ensure at least one edge
        missing_agent_graph_dict[agents[-2].name] = [agents[0]]

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(graph_dict=missing_agent_graph_dict, agents=agents)
        assert "agents in self.agents not in graph" in caplog.text
