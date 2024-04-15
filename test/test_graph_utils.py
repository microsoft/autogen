import logging
from typing import Any

import pytest

import autogen.graph_utils as gru
from autogen.agentchat import Agent


class FakeAgent(Agent):
    def __init__(self, name) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class TestHelpers:
    def test_has_self_loops(self):
        # Setup test data
        agents = [FakeAgent(name=f"Agent{i}") for i in range(3)]
        allowed_speaker_transitions = {
            agents[0]: [agents[1], agents[2]],
            agents[1]: [agents[2]],
            agents[2]: [agents[0]],
        }
        allowed_speaker_transitions_with_self_loops = {
            agents[0]: [agents[0], agents[1], agents[2]],
            agents[1]: [agents[1], agents[2]],
            agents[2]: [agents[0]],
        }

        # Testing
        assert not gru.has_self_loops(allowed_speaker_transitions)
        assert gru.has_self_loops(allowed_speaker_transitions_with_self_loops)


class TestGraphUtilCheckGraphValidity:
    def test_valid_structure(self):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]
        valid_speaker_transitions_dict = {agent: [other_agent for other_agent in agents] for agent in agents}
        gru.check_graph_validity(allowed_speaker_transitions_dict=valid_speaker_transitions_dict, agents=agents)

    def test_graph_with_invalid_structure(self):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]
        unseen_agent = FakeAgent("unseen_agent")
        invalid_speaker_transitions_dict = {unseen_agent: ["stranger"]}
        with pytest.raises(ValueError):
            gru.check_graph_validity(invalid_speaker_transitions_dict, agents)

    def test_graph_with_invalid_string(self):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]
        invalid_speaker_transitions_dict = {
            agent: ["agent1"] for agent in agents
        }  # 'agent1' is a string, not an Agent. Therefore raises an error.
        with pytest.raises(ValueError):
            gru.check_graph_validity(invalid_speaker_transitions_dict, agents)

    def test_graph_with_invalid_key(self):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]
        with pytest.raises(ValueError):
            gru.check_graph_validity({1: 1}, agents)

    # Test for Warning 1: Isolated agent nodes
    def test_isolated_agent_nodes_warning(self, caplog):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]
        # Create a speaker_transitions_dict where at least one agent is isolated
        speaker_transitions_dict_with_isolation = {agents[0]: [agents[0], agents[1]], agents[1]: [agents[0]]}
        # Add an isolated agent
        speaker_transitions_dict_with_isolation[agents[2]] = []

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(
                allowed_speaker_transitions_dict=speaker_transitions_dict_with_isolation, agents=agents
            )
        assert "isolated" in caplog.text

    # Test for Warning 2: Warning if the set of agents in allowed_speaker_transitions do not match agents
    def test_warning_for_mismatch_in_agents(self, caplog):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]

        # Test with missing agents in allowed_speaker_transitions_dict

        unknown_agent_dict = {
            agents[0]: [agents[0], agents[1], agents[2]],
            agents[1]: [agents[0], agents[1], agents[2]],
            agents[2]: [agents[0], agents[1], agents[2], FakeAgent("unknown_agent")],
        }

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(allowed_speaker_transitions_dict=unknown_agent_dict, agents=agents)

        assert "allowed_speaker_transitions do not match agents" in caplog.text

    # Test for Warning 3: Warning if there is duplicated agents in allowed_speaker_transitions_dict
    def test_warning_for_duplicate_agents(self, caplog):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]

        # Construct an `allowed_speaker_transitions_dict` with duplicated agents
        duplicate_agents_dict = {
            agents[0]: [agents[0], agents[1], agents[2]],
            agents[1]: [agents[0], agents[1], agents[2], agents[1]],
            agents[2]: [agents[0], agents[1], agents[2], agents[0], agents[2]],
        }

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(allowed_speaker_transitions_dict=duplicate_agents_dict, agents=agents)

        assert "duplicate" in caplog.text


class TestGraphUtilInvertDisallowedToAllowed:
    def test_basic_functionality(self):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]
        disallowed_graph = {agents[0]: [agents[1]], agents[1]: [agents[0], agents[2]], agents[2]: []}
        expected_allowed_graph = {
            agents[0]: [agents[0], agents[2]],
            agents[1]: [agents[1]],
            agents[2]: [agents[0], agents[1], agents[2]],
        }

        # Compare names of agents
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_empty_disallowed_graph(self):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]
        disallowed_graph = {}
        expected_allowed_graph = {
            agents[0]: [agents[0], agents[1], agents[2]],
            agents[1]: [agents[0], agents[1], agents[2]],
            agents[2]: [agents[0], agents[1], agents[2]],
        }

        # Compare names of agents
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_fully_disallowed_graph(self):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]

        disallowed_graph = {
            agents[0]: [agents[0], agents[1], agents[2]],
            agents[1]: [agents[0], agents[1], agents[2]],
            agents[2]: [agents[0], agents[1], agents[2]],
        }
        expected_allowed_graph = {agents[0]: [], agents[1]: [], agents[2]: []}

        # Compare names of agents
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_disallowed_graph_with_nonexistent_agent(self):
        agents = [FakeAgent("agent1"), FakeAgent("agent2"), FakeAgent("agent3")]

        disallowed_graph = {agents[0]: [FakeAgent("nonexistent_agent")]}
        # In this case, the function should ignore the nonexistent agent and proceed with the inversion
        expected_allowed_graph = {
            agents[0]: [agents[0], agents[1], agents[2]],
            agents[1]: [agents[0], agents[1], agents[2]],
            agents[2]: [agents[0], agents[1], agents[2]],
        }
        # Compare names of agents
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph
