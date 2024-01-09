import autogen
import pytest
import sys
import os
from io import StringIO
import logging
from unittest.mock import MagicMock
import unittest
from autogen.agentchat.groupchat import Agent, ConversableAgent
from autogen.agentchat.assistant_agent import AssistantAgent

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402


try:
    from autogen.agentchat.contrib.graphgroupchat import GraphGroupChat  # noqa: E402

    skip_test = True
except (ModuleNotFoundError, ImportError):
    skip_test = False

config_list = autogen.config_list_from_json(
    OAI_CONFIG_LIST, file_location=KEY_LOC, filter_dict={"api_type": ["openai"]}
)

# config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, filter_dict={"model": ["dev-oai-gpt4"]})

# assert len(config_list) > 0



@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip_test,
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphGroupChatSelectSpeakerThreeAssistantAgents:
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
        # Overridden random.choice to always return agent2
        with unittest.mock.patch("random.choice", return_value=self.agent2):
            selected_speaker = chat.select_speaker(last_speaker=self.agent3, selector=self.selector)
        assert selected_speaker.name == "bob"


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip_test,
    reason="do not run on MacOS or windows or dependency is not installed",
)
class TestGraphGroupChatSelectSpeakerOneAssistantAgentOneUserProxy:
    @pytest.fixture(autouse=True)
    def setup(self):
        # The default config list in notebook.
        self.llm_config = {"config_list": config_list, "cache_seed": 100}

        # Mock Agents
        self.agent1 = AssistantAgent(name="alice", llm_config=self.llm_config)

        # Termination message detection
        def is_termination_msg(content) -> bool:
            have_content = content.get("content", None) is not None
            if have_content and "TERMINATE" in content["content"]:
                return True
            return False

        # Terminates the conversation when TERMINATE is detected.
        self.user_proxy = autogen.UserProxyAgent(
            name="User_proxy",
            system_message="Terminator admin.",
            code_execution_config=False,
            is_termination_msg=is_termination_msg,
            human_input_mode="NEVER",
        )

        self.agents = [self.user_proxy, self.agent1]

        # Create Graph
        self.graph = nx.DiGraph()

        # Add nodes for all agents
        for agent in self.agents:
            self.graph.add_node(agent.name, first_round_speaker=True)
        # Add edges between all agents
        for agent1 in self.agents:
            for agent2 in self.agents:
                if agent1 != agent2:
                    self.graph.add_edge(agent1.name, agent2.name)

    def test_interaction(self):
        graph_group_chat = GraphGroupChat(
            agents=self.agents, messages=[], max_round=20, graph=self.graph  # Include all agents
        )

        # Create the manager
        manager = autogen.GroupChatManager(groupchat=graph_group_chat, llm_config=self.llm_config)

        # Initiates the chat with Alice
        self.agents[0].initiate_chat(
            manager,
            message="""Ask alice what is the largest single digit prime number without code.""",
        )

        # Assert the messages contain 7
        # don't just check the last message
        assert any("7" in message["content"] for message in graph_group_chat.messages)

        # Assert the messages contain alice
        assert any("alice" in message["name"] for message in graph_group_chat.messages)
