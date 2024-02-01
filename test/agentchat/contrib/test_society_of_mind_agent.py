import pytest
import sys
import autogen
import os
from autogen.agentchat.contrib.society_of_mind_agent import SocietyOfMindAgent


def test_society_of_mind_agent():
    external_agent = autogen.ConversableAgent(
        "external_agent",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is an external agent speaking.",
    )

    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
    )
    agent3 = autogen.ConversableAgent(
        "sam",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is sam speaking. TERMINATE",
    )

    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    group_chat_manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=False,
        is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    )

    soc = SocietyOfMindAgent("soc_agent", chat_manager=group_chat_manager)

    external_agent.send("An external message to kick things off.", soc, request_reply=True, silent=False)

    # Verify some properties of this conversation
    assert len(external_agent.chat_messages[soc]) == 2
    assert external_agent.chat_messages[soc][-1]["content"] == "This is sam speaking."
    assert len(groupchat.messages) == 4
    assert groupchat.messages[0]["name"] == "soc_agent"
    assert groupchat.messages[0]["content"] == "An external message to kick things off."
    assert groupchat.messages[1]["name"] == "alice"
    assert groupchat.messages[1]["content"] == "This is alice speaking."
    assert groupchat.messages[2]["name"] == "bob"
    assert groupchat.messages[2]["content"] == "This is bob speaking."
    assert groupchat.messages[3]["name"] == "sam"
    assert groupchat.messages[3]["content"] == "This is sam speaking. TERMINATE"

    assert len(agent1.chat_messages[group_chat_manager]) == 3  # Everything but the termination message
    assert len(agent2.chat_messages[group_chat_manager]) == 3  # Everything but the termination message
    assert len(agent3.chat_messages[group_chat_manager]) == 4  # Everything *including* the termination message

    assert len(group_chat_manager.chat_messages[agent1]) == 3  # Everything but the termination message
    assert len(group_chat_manager.chat_messages[agent2]) == 3  # Everything but the termination message
    assert len(group_chat_manager.chat_messages[agent3]) == 4  # Everything *including* the termination message

    # Let's go again. It should reset the inner monologue, but keep the external monologue
    external_agent.send("A second message to see how things go.", soc, request_reply=True, silent=False)
    assert len(external_agent.chat_messages[soc]) == 4
    assert external_agent.chat_messages[soc][0]["content"] == "An external message to kick things off."
    assert external_agent.chat_messages[soc][1]["content"] == "This is sam speaking."
    assert external_agent.chat_messages[soc][2]["content"] == "A second message to see how things go."
    assert external_agent.chat_messages[soc][3]["content"] == "This is sam speaking."
    assert len(groupchat.messages) == 4
    assert groupchat.messages[0]["name"] == "soc_agent"
    assert groupchat.messages[0]["content"] == "A second message to see how things go."
    assert groupchat.messages[1]["name"] == "alice"
    assert groupchat.messages[1]["content"] == "This is alice speaking."
    assert groupchat.messages[2]["name"] == "bob"
    assert groupchat.messages[2]["content"] == "This is bob speaking."
    assert groupchat.messages[3]["name"] == "sam"
    assert groupchat.messages[3]["content"] == "This is sam speaking. TERMINATE"

    assert (
        len(agent1.chat_messages[group_chat_manager]) == 5
    )  # Prior external conversation + everything but the termination message
    assert (
        len(agent2.chat_messages[group_chat_manager]) == 5
    )  # Prior external conversation + everything but the termination message
    assert (
        len(agent3.chat_messages[group_chat_manager]) == 6
    )  # Prior external conversation + everything *including* the termination message

    assert (
        len(group_chat_manager.chat_messages[agent1]) == 5
    )  # Prior external conversation + everything but the termination message
    assert (
        len(group_chat_manager.chat_messages[agent2]) == 5
    )  # Prior external conversation + everything but the termination message
    assert (
        len(group_chat_manager.chat_messages[agent3]) == 6
    )  # Prior external conversation + everything *including* the termination message

    assert agent1.chat_messages[group_chat_manager][0]["content"] == "An external message to kick things off."
    assert agent1.chat_messages[group_chat_manager][0]["role"] == "user"
    assert group_chat_manager.chat_messages[agent1][0]["role"] == "assistant"

    assert agent1.chat_messages[group_chat_manager][1]["content"] == "This is sam speaking."
    assert agent1.chat_messages[group_chat_manager][1]["role"] == "user"
    assert group_chat_manager.chat_messages[agent1][1]["role"] == "assistant"

    assert agent1.chat_messages[group_chat_manager][2]["content"] == "A second message to see how things go."
    assert agent1.chat_messages[group_chat_manager][2]["role"] == "user"
    assert group_chat_manager.chat_messages[agent1][2]["role"] == "assistant"

    assert agent1.chat_messages[group_chat_manager][3]["content"] == "This is alice speaking."
    assert agent1.chat_messages[group_chat_manager][3]["role"] == "assistant"
    assert group_chat_manager.chat_messages[agent1][3]["role"] == "user"

    assert agent1.chat_messages[group_chat_manager][4]["content"] == "This is bob speaking."
    assert agent1.chat_messages[group_chat_manager][4]["role"] == "user"
    assert group_chat_manager.chat_messages[agent1][4]["role"] == "assistant"

    for i in range(0, 5):
        assert (
            agent1.chat_messages[group_chat_manager][i]["content"]
            == agent3.chat_messages[group_chat_manager][i]["content"]
        )
    assert agent3.chat_messages[group_chat_manager][5]["content"] == "This is sam speaking. TERMINATE"


def test_custom_preparer():
    external_agent = autogen.ConversableAgent(
        "external_agent",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is an external agent speaking.",
    )

    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
    )
    agent3 = autogen.ConversableAgent(
        "sam",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is sam speaking. TERMINATE",
    )

    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    group_chat_manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=False,
        is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    )

    def custom_preparer(self, messages):
        assert isinstance(self, SocietyOfMindAgent)
        assert len(messages) == 4
        assert messages[0]["content"] == "An external message to kick things off."
        assert messages[1]["content"] == "This is alice speaking."
        assert messages[2]["content"] == "This is bob speaking."
        assert messages[3]["content"] == "This is sam speaking. TERMINATE"
        return "All tests passed."

    soc = SocietyOfMindAgent("soc_agent", chat_manager=group_chat_manager, response_preparer=custom_preparer)

    external_agent.send("An external message to kick things off.", soc, request_reply=True, silent=False)

    # Verify some properties of this conversation
    assert len(external_agent.chat_messages[soc]) == 2
    assert external_agent.chat_messages[soc][-1]["content"] == "All tests passed."


if __name__ == "__main__":
    test_society_of_mind_agent()
    test_custom_preparer()
