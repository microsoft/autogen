import pytest
import autogen
import json


def test_func_call_groupchat():
    agent1 = autogen.ConversableAgent(
        "alice",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
        function_map={"test_func": lambda x: x},
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2], messages=[], max_round=3)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent2.initiate_chat(group_chat_manager, message={"function_call": {"name": "test_func", "arguments": '{"x": 1}'}})

    assert len(groupchat.messages) == 3
    assert (
        groupchat.messages[-2]["role"] == "function"
        and groupchat.messages[-2]["name"] == "test_func"
        and groupchat.messages[-2]["content"] == "1"
    )
    assert groupchat.messages[-1]["name"] == "alice"

    agent3 = autogen.ConversableAgent(
        "carol",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is carol speaking.",
        function_map={"test_func": lambda x: x + 1},
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2, agent3], messages=[], max_round=3)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent3.initiate_chat(group_chat_manager, message={"function_call": {"name": "test_func", "arguments": '{"x": 1}'}})

    assert (
        groupchat.messages[-2]["role"] == "function"
        and groupchat.messages[-2]["name"] == "test_func"
        and groupchat.messages[-2]["content"] == "1"
    )
    assert groupchat.messages[-1]["name"] == "carol"

    agent2.initiate_chat(group_chat_manager, message={"function_call": {"name": "func", "arguments": '{"x": 1}'}})


def test_chat_manager():
    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2], messages=[], max_round=2)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent1.initiate_chat(group_chat_manager, message="hello")

    assert len(agent1.chat_messages[group_chat_manager]) == 2
    assert len(groupchat.messages) == 2

    group_chat_manager.reset()
    assert len(groupchat.messages) == 0
    agent1.reset()
    agent2.reset()
    agent2.initiate_chat(group_chat_manager, message="hello")
    assert len(groupchat.messages) == 2

    with pytest.raises(ValueError):
        agent2.initiate_chat(group_chat_manager, message={"function_call": {"name": "func", "arguments": '{"x": 1}'}})


def test_plugin():
    # Give another Agent class ability to manage group chat
    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2], messages=[], max_round=2)
    group_chat_manager = autogen.ConversableAgent(name="deputy_manager", llm_config=False)
    group_chat_manager.register_reply(
        autogen.Agent,
        reply_func=autogen.GroupChatManager.run_chat,
        config=groupchat,
        reset_config=autogen.GroupChat.reset,
    )
    agent1.initiate_chat(group_chat_manager, message="hello")

    assert len(agent1.chat_messages[group_chat_manager]) == 2
    assert len(groupchat.messages) == 2


def test_agent_mentions():
    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
    )
    agent3 = autogen.ConversableAgent(
        "sam",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is sam speaking.",
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2, agent3], messages=[], max_round=2)

    # Basic counting
    assert json.dumps(groupchat._mentioned_agents("", [agent1, agent2, agent3]), sort_keys=True) == "{}"
    assert json.dumps(groupchat._mentioned_agents("alice", [agent1, agent2, agent3]), sort_keys=True) == '{"alice": 1}'
    assert (
        json.dumps(groupchat._mentioned_agents("alice bob alice", [agent1, agent2, agent3]), sort_keys=True)
        == '{"alice": 2, "bob": 1}'
    )
    assert (
        json.dumps(groupchat._mentioned_agents("alice bob alice sam", [agent1, agent2, agent3]), sort_keys=True)
        == '{"alice": 2, "bob": 1, "sam": 1}'
    )
    assert (
        json.dumps(groupchat._mentioned_agents("alice bob alice sam robert", [agent1, agent2, agent3]), sort_keys=True)
        == '{"alice": 2, "bob": 1, "sam": 1}'
    )

    # Substring
    assert (
        json.dumps(groupchat._mentioned_agents("sam samantha basam asami", [agent1, agent2, agent3]), sort_keys=True)
        == '{"sam": 1}'
    )

    # Word boundaries
    assert (
        json.dumps(groupchat._mentioned_agents("alice! .alice. .alice", [agent1, agent2, agent3]), sort_keys=True)
        == '{"alice": 3}'
    )

    # Special characters in agent names
    agent4 = autogen.ConversableAgent(
        ".*",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="Match everything.",
    )

    groupchat = autogen.GroupChat(agents=[agent1, agent2, agent3, agent4], messages=[], max_round=2)
    assert (
        json.dumps(
            groupchat._mentioned_agents("alice bob alice sam robert .*", [agent1, agent2, agent3, agent4]),
            sort_keys=True,
        )
        == '{".*": 1, "alice": 2, "bob": 1, "sam": 1}'
    )


if __name__ == "__main__":
    test_func_call_groupchat()
    # test_broadcast()
    test_chat_manager()
    # test_plugin()
    # test_agent_mentions()
