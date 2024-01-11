import sys
import pytest
import logging
from autogen.agentchat.groupchat import Agent
import autogen.graph_utils as gru


# Define pytest fixtures for agents and valid_speaker_order_dict
@pytest.fixture
def agents():
    return [Agent("agent1"), Agent("agent2"), Agent("agent3")]


@pytest.fixture
def valid_speaker_order_dict(agents):
    return {agent.name: [other_agent for other_agent in agents if other_agent != agent] for agent in agents}


# Use pytest.mark.skipif decorator for conditional skipping
@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphUtilCheckGraphValidity:
    def test_valid_structure(self, agents, valid_speaker_order_dict):
        gru.check_graph_validity(allowed_speaker_order_dict=valid_speaker_order_dict, agents=agents)

    def test_graph_with_invalid_structure(self, agents):
        invalid_speaker_order_dict = {"unseen_agent": ["stranger"]}
        with pytest.raises(ValueError):
            gru.check_graph_validity(invalid_speaker_order_dict, agents)

    def test_graph_with_invalid_string(self, agents):
        invalid_speaker_order_dict = {
            agent.name: ["agent1"] for agent in agents
        }  # 'agent1' is a string, not an Agent. Therefore raises an error.
        with pytest.raises(ValueError):
            gru.check_graph_validity(invalid_speaker_order_dict, agents)

    def test_graph_with_no_nodes(self, agents):
        empty_speaker_order_dict = {}
        with pytest.raises(ValueError):
            gru.check_graph_validity(empty_speaker_order_dict, agents)

    def test_graph_with_no_edges(self, agents):
        speaker_order_dict_no_edges = {agent.name: [] for agent in agents}
        with pytest.raises(ValueError):
            gru.check_graph_validity(speaker_order_dict_no_edges, agents)

    def test_graph_with_self_loops(self, agents):
        speaker_order_dict_with_self_loop = {agent.name: [agent.name] for agent in agents}
        with pytest.raises(ValueError):
            gru.check_graph_validity(speaker_order_dict_with_self_loop, agents, allow_repeat_speaker=False)

    # Test for Warning 1: Isolated agent nodes
    def test_isolated_agent_nodes_warning(self, agents, caplog):
        # Create a graph where at least one agent is isolated
        speaker_order_dict_with_isolation = {agents[0].name: [agents[1]], agents[1].name: [agents[0]]}
        # Add an isolated agent
        speaker_order_dict_with_isolation[agents[2].name] = []

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(allowed_speaker_order_dict=speaker_order_dict_with_isolation, agents=agents)
        assert "isolated agent nodes" in caplog.text

    # Test for Warning 2: Agents not in graph
    def test_agents_not_in_graph_warning(self, agents, caplog):
        # Create a graph where all but the last agent are connected in a simple chain to ensure no isolated nodes and at least one edge
        missing_agent_speaker_order_dict = {agents[i].name: [agents[i + 1]] for i in range(len(agents) - 2)}
        # Add a connection back to the first agent to close the chain and ensure at least one edge
        missing_agent_speaker_order_dict[agents[-2].name] = [agents[0]]

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(allowed_speaker_order_dict=missing_agent_speaker_order_dict, agents=agents)
        assert "agents in self.agents not in graph" in caplog.text


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphUtilInvertDisallowedToAllowed:
    def test_basic_functionality(self, agents):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        disallowed_graph = {"agent1": [agents[1]], "agent2": [agents[0], agents[2]], "agent3": []}
        expected_allowed_graph = {
            "agent1": [agents[0], agents[2]],
            "agent2": [agents[1]],
            "agent3": [agents[0], agents[1], agents[2]],
        }

        # Compare names of agents in the allowed graph
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_empty_disallowed_graph(self, agents):
        disallowed_graph = {}
        expected_allowed_graph = {
            "agent1": [agents[0], agents[1], agents[2]],
            "agent2": [agents[0], agents[1], agents[2]],
            "agent3": [agents[0], agents[1], agents[2]],
        }

        # Compare names of agents in the allowed graph
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_fully_disallowed_graph(self, agents):
        disallowed_graph = {
            "agent1": [agents[0], agents[1], agents[2]],
            "agent2": [agents[0], agents[1], agents[2]],
            "agent3": [agents[0], agents[1], agents[2]],
        }
        expected_allowed_graph = {"agent1": [], "agent2": [], "agent3": []}

        # Compare names of agents in the allowed graph
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_disallowed_graph_with_nonexistent_agent(self, agents):
        disallowed_graph = {"agent1": [Agent("nonexistent_agent")]}
        # In this case, the function should ignore the nonexistent agent and proceed with the inversion
        expected_allowed_graph = {
            "agent1": [agents[0], agents[1], agents[2]],
            "agent2": [agents[0], agents[1], agents[2]],
            "agent3": [agents[0], agents[1], agents[2]],
        }
        # Compare names of agents in the allowed graph
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph
