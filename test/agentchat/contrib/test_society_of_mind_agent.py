#!/usr/bin/env python3 -m pytest

import pytest
import sys
import autogen
import os
from typing_extensions import Annotated
from autogen.agentchat.contrib.society_of_mind_agent import SocietyOfMindAgent

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from conftest import skip_openai  # noqa: E402

if not skip_openai:
    config_list = autogen.config_list_from_json(env_or_file=OAI_CONFIG_LIST, file_location=KEY_LOC)


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

    assert len(agent1.chat_messages[group_chat_manager]) == 4  # Everything *including* the termination message
    assert len(agent2.chat_messages[group_chat_manager]) == 4  # Everything *including* the termination message
    assert len(agent3.chat_messages[group_chat_manager]) == 4  # Everything *including* the termination message

    assert len(group_chat_manager.chat_messages[agent1]) == 4  # Everything *including* the termination message
    assert len(group_chat_manager.chat_messages[agent2]) == 4  # Everything *including* the termination message
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
        len(agent1.chat_messages[group_chat_manager]) == 6
    )  # Prior external conversation + everything including the termination message
    assert (
        len(agent2.chat_messages[group_chat_manager]) == 6
    )  # Prior external conversation + everything including the termination message
    assert (
        len(agent3.chat_messages[group_chat_manager]) == 6
    )  # Prior external conversation + everything *including* the termination message

    assert (
        len(group_chat_manager.chat_messages[agent1]) == 6
    )  # Prior external conversation + everything including the termination message
    assert (
        len(group_chat_manager.chat_messages[agent2]) == 6
    )  # Prior external conversation + everything including the termination message
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


@pytest.mark.skipif(
    skip_openai,
    reason="do not run openai tests",
)
def test_function_calling():
    llm_config = {"config_list": config_list}
    inner_llm_config = {
        "config_list": config_list,
        "functions": [
            {
                "name": "reverse_print",
                "description": "Prints a string in reverse",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "str": {
                            "type": "string",
                            "description": "The string to reverse-print",
                        }
                    },
                },
                "required": ["str"],
            }
        ],
    }

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
        llm_config=inner_llm_config,
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
        default_auto_reply="TERMINATE",
    )

    agent2.register_function(
        function_map={
            "reverse_print": lambda str: str[::-1],
        }
    )

    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    group_chat_manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=False,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    soc = SocietyOfMindAgent("soc_agent", chat_manager=group_chat_manager, llm_config=llm_config)
    external_agent.send(
        "Call the reverse_print function with the str 'Hello world.'", soc, request_reply=True, silent=False
    )


@pytest.mark.skipif(
    skip_openai,
    reason="do not run openai tests",
)
def test_tool_use():
    llm_config = {"config_list": config_list}
    inner_llm_config = {"config_list": config_list}

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
        llm_config=inner_llm_config,
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
        default_auto_reply="TERMINATE",
    )

    @agent2.register_for_execution()
    @agent1.register_for_llm(name="reverse_print", description="Prints a string in reverse")
    def _reverse_print(s: Annotated[str, "The string to reverse-print."]) -> str:
        return s[::-1]

    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    group_chat_manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=False,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    soc = SocietyOfMindAgent("soc_agent", chat_manager=group_chat_manager, llm_config=llm_config)
    external_agent.send("Call reverse_print with the str 'Hello world.'", soc, request_reply=True, silent=False)


if __name__ == "__main__":
    # test_society_of_mind_agent()
    # test_custom_preparer()
    test_function_calling()
    test_tool_use()
