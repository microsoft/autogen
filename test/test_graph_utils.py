import sys
import pytest
import logging
from autogen.agentchat.groupchat import Agent
import autogen.graph_utils as gru


# Use pytest.mark.skipif decorator for conditional skipping
@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestHelpers:
    # Tests for get_successor_agent_names
    def test_get_successor_agent_names(self):
        # Setup test data
        agents = [Agent(name=f"Agent{i}") for i in range(3)]
        allowed_speaker_transitions = {
            agents[0].name: [agents[1], agents[2]],
            agents[1].name: [agents[2]],
            agents[2].name: [agents[0]],
        }

        # Testing
        assert gru.get_successor_agent_names(agents[0].name, allowed_speaker_transitions) == [
            agents[1].name,
            agents[2].name,
        ]
        assert gru.get_successor_agent_names(agents[1].name, allowed_speaker_transitions) == [agents[2].name]
        assert gru.get_successor_agent_names(agents[2].name, allowed_speaker_transitions) == [agents[0].name]

        # Test with an agent not in the dictionary
        with pytest.raises(KeyError):
            gru.get_successor_agent_names("NonExistentAgent", allowed_speaker_transitions)

    # Tests for get_predecessor_agent_names
    def test_get_predecessor_agent_names(self):
        # Setup test data
        agents = [Agent(name=f"Agent{i}") for i in range(3)]
        allowed_speaker_transitions = {
            agents[0].name: [agents[1], agents[2]],
            agents[1].name: [agents[2]],
            agents[2].name: [agents[0]],
        }

        # Testing
        assert gru.get_predecessor_agent_names(agents[1].name, allowed_speaker_transitions) == [agents[0].name]
        assert gru.get_predecessor_agent_names(agents[2].name, allowed_speaker_transitions) == [
            agents[0].name,
            agents[1].name,
        ]
        assert gru.get_predecessor_agent_names(agents[0].name, allowed_speaker_transitions) == [agents[2].name]

        # Test with an agent not in the dictionary
        assert gru.get_predecessor_agent_names("NonExistentAgent", allowed_speaker_transitions) == []

    def test_has_self_loops(self):
        # Setup test data
        agents = [Agent(name=f"Agent{i}") for i in range(3)]
        allowed_speaker_transitions = {
            agents[0].name: [agents[1], agents[2]],
            agents[1].name: [agents[2]],
            agents[2].name: [agents[0]],
        }
        allowed_speaker_transitions_with_self_loops = {
            agents[0].name: [agents[0], agents[1], agents[2]],
            agents[1].name: [agents[1], agents[2]],
            agents[2].name: [agents[0]],
        }

        # Testing
        assert not gru.has_self_loops(allowed_speaker_transitions)
        assert gru.has_self_loops(allowed_speaker_transitions_with_self_loops)


# Use pytest.mark.skipif decorator for conditional skipping
@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphUtilCheckGraphValidity:
    def test_valid_structure(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        valid_speaker_transitions_dict = {agent.name: [other_agent for other_agent in agents] for agent in agents}
        gru.check_graph_validity(allowed_speaker_transitions_dict=valid_speaker_transitions_dict, agents=agents)

    def test_graph_with_invalid_structure(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        invalid_speaker_transitions_dict = {"unseen_agent": ["stranger"]}
        with pytest.raises(ValueError):
            gru.check_graph_validity(invalid_speaker_transitions_dict, agents)

    def test_graph_with_invalid_string(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        invalid_speaker_transitions_dict = {
            agent.name: ["agent1"] for agent in agents
        }  # 'agent1' is a string, not an Agent. Therefore raises an error.
        with pytest.raises(ValueError):
            gru.check_graph_validity(invalid_speaker_transitions_dict, agents)

    def test_graph_with_self_loops(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        speaker_transitions_dict_with_self_loop = {agent.name: [agent.name] for agent in agents}
        with pytest.raises(ValueError):
            gru.check_graph_validity(speaker_transitions_dict_with_self_loop, agents, allow_repeat_speaker=False)

    def test_graph_with_unauthorized_self_loops(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        # Creating a subset of agents allowed to have self-loops
        allowed_repeat_speakers = agents[: len(agents) // 2]
        allowed_repeat_speaker_agents = [agent for agent in allowed_repeat_speakers]

        # Constructing a speaker order dictionary with self-loops for all agents
        # Ensuring at least one agent outside the allowed_repeat_speakers has a self-loop
        speaker_transitions_dict_with_self_loop = {}
        for agent in agents:
            if agent in allowed_repeat_speakers:
                speaker_transitions_dict_with_self_loop[agent.name] = [agent.name]  # Allowed self-loop
            else:
                speaker_transitions_dict_with_self_loop[agent.name] = [agent.name]  # Unauthorized self-loop

        # Testing the function with the constructed speaker order dict
        with pytest.raises(ValueError):
            gru.check_graph_validity(
                speaker_transitions_dict_with_self_loop, agents, allow_repeat_speaker=allowed_repeat_speaker_agents
            )

    # Test for Warning 1: Isolated agent nodes
    def test_isolated_agent_nodes_warning(self, caplog):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        # Create a speaker_transitions_dict where at least one agent is isolated
        speaker_transitions_dict_with_isolation = {agents[0].name: [agents[0], agents[1]], agents[1].name: [agents[0]]}
        # Add an isolated agent
        speaker_transitions_dict_with_isolation[agents[2].name] = []

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(
                allowed_speaker_transitions_dict=speaker_transitions_dict_with_isolation, agents=agents
            )
        assert "isolated" in caplog.text

    # Test for Warning 2: Warning if the set of agents in allowed_speaker_transitions do not match agents
    def test_warning_for_mismatch_in_agents(self, caplog):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]

        # Test with missing agents in allowed_speaker_transitions_dict

        unknown_agent_dict = {
            "agent1": [agents[0], agents[1], agents[2]],
            "agent2": [agents[0], agents[1], agents[2]],
            "agent3": [agents[0], agents[1], agents[2], Agent("unknown_agent")],
        }

        with caplog.at_level(logging.WARNING):
            gru.check_graph_validity(allowed_speaker_transitions_dict=unknown_agent_dict, agents=agents)

        assert "allowed_speaker_transitions do not match agents" in caplog.text


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"],
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphUtilInvertDisallowedToAllowed:
    def test_basic_functionality(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        disallowed_graph = {"agent1": [agents[1]], "agent2": [agents[0], agents[2]], "agent3": []}
        expected_allowed_graph = {
            "agent1": [agents[0], agents[2]],
            "agent2": [agents[1]],
            "agent3": [agents[0], agents[1], agents[2]],
        }

        # Compare names of agents
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_empty_disallowed_graph(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]
        disallowed_graph = {}
        expected_allowed_graph = {
            "agent1": [agents[0], agents[1], agents[2]],
            "agent2": [agents[0], agents[1], agents[2]],
            "agent3": [agents[0], agents[1], agents[2]],
        }

        # Compare names of agents
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_fully_disallowed_graph(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]

        disallowed_graph = {
            "agent1": [agents[0], agents[1], agents[2]],
            "agent2": [agents[0], agents[1], agents[2]],
            "agent3": [agents[0], agents[1], agents[2]],
        }
        expected_allowed_graph = {"agent1": [], "agent2": [], "agent3": []}

        # Compare names of agents
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph

    def test_disallowed_graph_with_nonexistent_agent(self):
        agents = [Agent("agent1"), Agent("agent2"), Agent("agent3")]

        disallowed_graph = {"agent1": [Agent("nonexistent_agent")]}
        # In this case, the function should ignore the nonexistent agent and proceed with the inversion
        expected_allowed_graph = {
            "agent1": [agents[0], agents[1], agents[2]],
            "agent2": [agents[0], agents[1], agents[2]],
            "agent3": [agents[0], agents[1], agents[2]],
        }
        # Compare names of agents
        inverted = gru.invert_disallowed_to_allowed(disallowed_graph, agents)
        assert inverted == expected_allowed_graph
