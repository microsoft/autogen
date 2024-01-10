import pytest
from unittest import mock
import builtins
import autogen
import json


def test_func_call_groupchat():
    agent1 = autogen.ConversableAgent(
        "alice",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
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
        default_auto_reply="This is alice speaking.",
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


def _test_selection_method(method: str):
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
        "charlie",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is charlie speaking.",
    )

    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3],
        messages=[],
        max_round=6,
        speaker_selection_method=method,
        allow_repeat_speaker=False if method == "manual" else True,
    )
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)

    if method == "round_robin":
        agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")
        assert len(agent1.chat_messages[group_chat_manager]) == 6
        assert len(groupchat.messages) == 6
        assert [msg["content"] for msg in agent1.chat_messages[group_chat_manager]] == [
            "This is alice speaking.",
            "This is bob speaking.",
            "This is charlie speaking.",
        ] * 2
    elif method == "auto":
        agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")
        assert len(agent1.chat_messages[group_chat_manager]) == 6
        assert len(groupchat.messages) == 6
    elif method == "random":
        agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")
        assert len(agent1.chat_messages[group_chat_manager]) == 6
        assert len(groupchat.messages) == 6
    elif method == "manual":
        for user_input in ["", "q", "x", "1", "10"]:
            with mock.patch.object(builtins, "input", lambda _: user_input):
                group_chat_manager.reset()
                agent1.reset()
                agent2.reset()
                agent3.reset()
                agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")
                if user_input == "1":
                    assert len(agent1.chat_messages[group_chat_manager]) == 6
                    assert len(groupchat.messages) == 6
                    assert [msg["content"] for msg in agent1.chat_messages[group_chat_manager]] == [
                        "This is alice speaking.",
                        "This is bob speaking.",
                        "This is alice speaking.",
                        "This is bob speaking.",
                        "This is alice speaking.",
                        "This is bob speaking.",
                    ]
                else:
                    assert len(agent1.chat_messages[group_chat_manager]) == 6
                    assert len(groupchat.messages) == 6
    elif method == "wrong":
        with pytest.raises(ValueError):
            agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")


def test_speaker_selection_method():
    for method in ["auto", "round_robin", "random", "manual", "wrong", "RounD_roBin"]:
        _test_selection_method(method)


def _test_n_agents_less_than_3(method):
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
    # test two agents
    groupchat = autogen.GroupChat(
        agents=[agent1, agent2],
        messages=[],
        max_round=6,
        speaker_selection_method=method,
        allow_repeat_speaker=[agent1, agent2] if method == "random" else False,
    )
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")
    assert len(agent1.chat_messages[group_chat_manager]) == 6
    assert len(groupchat.messages) == 6
    if method != "random" or method.lower() == "round_robin":
        assert [msg["content"] for msg in agent1.chat_messages[group_chat_manager]] == [
            "This is alice speaking.",
            "This is bob speaking.",
        ] * 3

    # test one agent
    groupchat = autogen.GroupChat(
        agents=[agent1],
        messages=[],
        max_round=6,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False,
    )
    with pytest.raises(ValueError):
        group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
        agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")

    # test zero agent
    groupchat = autogen.GroupChat(
        agents=[],
        messages=[],
        max_round=6,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False,
    )
    with pytest.raises(ValueError):
        group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
        agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")


def test_n_agents_less_than_3():
    for method in ["auto", "round_robin", "random", "RounD_roBin"]:
        _test_n_agents_less_than_3(method)


def test_plugin():
    # Give another Agent class ability to manage group chat
    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
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
        default_auto_reply="This is alice speaking.",
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


def test_termination():
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

    # Test empty is_termination_msg function
    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False, is_termination_msg=None)

    agent1.initiate_chat(group_chat_manager, message="'None' is_termination_msg function.")
    assert len(groupchat.messages) == 10

    # Test user-provided is_termination_msg function
    agent1.reset()
    agent2.reset()
    agent3.reset()

    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    group_chat_manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=False,
        is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    )

    agent1.initiate_chat(group_chat_manager, message="User-provided is_termination_msg function.")
    assert len(groupchat.messages) == 3


def test_next_agent():
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
        default_auto_reply="This is sam speaking.",
    )
    agent4 = autogen.ConversableAgent(
        "sally",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is sally speaking.",
    )

    # Test empty is_termination_msg function
    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    assert groupchat.next_agent(agent1, [agent1, agent2, agent3]) == agent2
    assert groupchat.next_agent(agent2, [agent1, agent2, agent3]) == agent3
    assert groupchat.next_agent(agent3, [agent1, agent2, agent3]) == agent1

    assert groupchat.next_agent(agent1) == agent2
    assert groupchat.next_agent(agent2) == agent3
    assert groupchat.next_agent(agent3) == agent1

    assert groupchat.next_agent(agent1, [agent1, agent3]) == agent3
    assert groupchat.next_agent(agent3, [agent1, agent3]) == agent1

    assert groupchat.next_agent(agent2, [agent1, agent3]) == agent3
    assert groupchat.next_agent(agent4, [agent1, agent3]) == agent1
    assert groupchat.next_agent(agent4, [agent1, agent2, agent3]) == agent1


def test_selection_helpers():
    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
        description="Alice is an AI agent.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        description="Bob is an AI agent.",
    )
    agent3 = autogen.ConversableAgent(
        "sam",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is sam speaking.",
        system_message="Sam is an AI agent.",
    )

    # Test empty is_termination_msg function
    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    select_speaker_msg = groupchat.select_speaker_msg()
    select_speaker_prompt = groupchat.select_speaker_prompt()

    assert "Alice is an AI agent." in select_speaker_msg
    assert "Bob is an AI agent." in select_speaker_msg
    assert "Sam is an AI agent." in select_speaker_msg
    assert str(["Alice", "Bob", "Sam"]).lower() in select_speaker_prompt.lower()

    with mock.patch.object(builtins, "input", lambda _: "1"):
        groupchat.manual_select_speaker()


if __name__ == "__main__":
    # test_func_call_groupchat()
    # test_broadcast()
    # test_chat_manager()
    # test_plugin()
    test_speaker_selection_method()
    # test_n_agents_less_than_3()
    # test_agent_mentions()
    # test_termination()
    test_next_agent()
