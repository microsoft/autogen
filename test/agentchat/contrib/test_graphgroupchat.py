try:
    import networkx as nx
    import matplotlib.pyplot as plt

    skip_test = False
except ImportError:
    skip_test = True

from autogen.agentchat.contrib.graphgroupchat import GraphGroupChat
from unittest import mock
import builtins
import autogen
import json
import sys
import os
import pytest
from unittest.mock import MagicMock
import unittest
from autogen.agentchat.groupchat import GroupChat, Agent, ConversableAgent
from autogen.agentchat.assistant_agent import AssistantAgent


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402


config_list = autogen.config_list_from_json(
    OAI_CONFIG_LIST, file_location=KEY_LOC, filter_dict={"api_type": ["openai"]}
)

# config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, filter_dict={"model": ["dev-oai-gpt4"]})

assert len(config_list) > 0


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip_test,
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphGroupChatGraphValidity:
    def test_graph_with_no_nodes(self):
        agents = [Agent(name="Agent 1"), Agent(name="Agent 2")]
        messages = []
        graph = nx.DiGraph()

        with pytest.raises(ValueError) as excinfo:
            GraphGroupChat(agents, messages, graph)
        assert "The graph has no nodes." in str(excinfo.value)

    def test_graph_with_no_edges(self):
        agents = [Agent(name="Agent 1"), Agent(name="Agent 2")]
        messages = []
        graph = nx.DiGraph()
        graph.add_node("Agent 1")

        with pytest.raises(ValueError) as excinfo:
            GraphGroupChat(agents, messages, graph)
        assert "The graph has no edges." in str(excinfo.value)

    def test_graph_with_no_first_round_speaker(self):
        agents = [Agent(name="Agent 1"), Agent(name="Agent 2")]
        messages = []
        graph = nx.DiGraph()
        graph.add_node("Agent 1")
        graph.add_edge("Agent 1", "Agent 2")

        with pytest.raises(ValueError) as excinfo:
            GraphGroupChat(agents, messages, graph)
        assert "The graph has no nodes with 'first_round_speaker' set to True." in str(excinfo.value)

    def test_graph_with_self_loops(self):
        agents = [Agent(name="Agent 1"), Agent(name="Agent 2")]
        messages = []
        graph = nx.DiGraph()
        graph.add_node("Agent 1", first_round_speaker=True)
        graph.add_node("Agent 2", first_round_speaker=False)
        graph.add_edge("Agent 1", "Agent 1")

        with pytest.raises(ValueError) as excinfo:
            GraphGroupChat(agents, messages, graph, allow_repeat_speaker=False)
        assert "The graph has self-loops, but self.allow_repeat_speaker is False." in str(excinfo.value)


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip_test,
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphGroupChatSelectSpeaker:
    @pytest.fixture(autouse=True)
    def setup(self):
        # The default config list in notebook.
        llm_config = {"config_list": config_list, "cache_seed": 100}

        # Mock Agents
        self.agent1 = AssistantAgent(name="alice", llm_config=llm_config)
        self.agent2 = AssistantAgent(name="bob", llm_config=llm_config)
        self.agent3 = AssistantAgent(name="charlie", llm_config=llm_config)

        # Mock ConversableAgent Selector
        self.selector = ConversableAgent(name="selector", llm_config=llm_config)
        self.selector.generate_oai_reply = MagicMock(return_value=(True, "bob"))

        # Create Graph
        self.graph = nx.DiGraph()
        self.graph.add_node(self.agent1.name, first_round_speaker=True)
        self.graph.add_node(self.agent2.name)
        self.graph.add_node(self.agent3.name)
        self.graph.add_edge(self.agent1.name, self.agent2.name)
        self.graph.add_edge(self.agent1.name, self.agent3.name)
        self.graph.add_edge(self.agent2.name, self.agent3.name)
        self.graph.add_edge(self.agent2.name, self.agent1.name)
        self.graph.add_edge(self.agent3.name, self.agent1.name)
        self.graph.add_edge(self.agent3.name, self.agent2.name)

        # Create agents
        self.agents = [self.agent1, self.agent2, self.agent3]

    def test_select_first_round_speaker(self):
        chat = GraphGroupChat(self.agents, [], self.graph)
        selected_speaker = chat.select_speaker(last_speaker=None, selector=self.selector)
        assert selected_speaker.name == "alice"

    def test_using_suggested_next_speaker(self):
        chat = GraphGroupChat(self.agents, [{"content": "Some message. NEXT: charlie"}], self.graph)
        selected_speaker = chat.select_speaker(last_speaker=self.agent1, selector=self.selector)
        assert selected_speaker.name == "charlie"

    def test_using_llm_to_pick_speaker(self):
        chat = GraphGroupChat(self.agents, [{"content": "Some message."}], self.graph)
        selected_speaker = chat.select_speaker(last_speaker=self.agent1, selector=self.selector)
        assert selected_speaker.name in ("bob", "charlie")

    def test_random_speaker_selection(self):
        chat = GraphGroupChat(self.agents, [], self.graph, allow_repeat_speaker=False)
        chat.previous_speaker = self.agent3
        # Overridde random.choice to always return agent2
        with unittest.mock.patch("random.choice", return_value=self.agent2):
            selected_speaker = chat.select_speaker(last_speaker=self.agent3, selector=self.selector)
        assert selected_speaker.name == "bob"
