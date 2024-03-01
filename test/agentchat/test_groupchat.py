#!/usr/bin/env python3 -m pytest

from typing import Any, Dict, List, Optional, Type
from autogen import AgentNameConflict
import pytest
from unittest import mock
import builtins
import autogen
import json
import sys
from autogen import Agent, GroupChat


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

    # test zero agent
    with pytest.raises(ValueError):
        groupchat = autogen.GroupChat(
            agents=[], messages=[], max_round=6, speaker_selection_method="round_robin", allow_repeat_speaker=False
        )
        group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
        agent1.initiate_chat(group_chat_manager, message="This is alice speaking.")


def test_invalid_allow_repeat_speaker():
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
    # test invalid allow_repeat_speaker
    with pytest.raises(ValueError) as e:
        autogen.GroupChat(
            agents=[agent1, agent2],
            messages=[],
            max_round=6,
            speaker_selection_method="round_robin",
            allow_repeat_speaker={},
        )
    assert str(e.value) == "GroupChat allow_repeat_speaker should be a bool or a list of Agents.", e.value


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


def test_send_intros():
    agent1 = autogen.ConversableAgent(
        "alice",
        description="The first agent.",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking. TERMINATE",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        description="The second agent.",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking. TERMINATE",
    )
    agent3 = autogen.ConversableAgent(
        "sam",
        description="The third agent.",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is sam speaking. TERMINATE",
    )
    agent4 = autogen.ConversableAgent(
        "sally",
        description="The fourth agent.",
        max_consecutive_auto_reply=10,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is sally speaking. TERMINATE",
    )

    # Test empty is_termination_msg function
    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3],
        messages=[],
        speaker_selection_method="round_robin",
        max_round=10,
        send_introductions=True,
    )

    intro = groupchat.introductions_msg()
    assert "The first agent." in intro
    assert "The second agent." in intro
    assert "The third agent." in intro
    assert "The fourth agent." not in intro

    intro = groupchat.introductions_msg([agent1, agent2, agent4])
    assert "The first agent." in intro
    assert "The second agent." in intro
    assert "The third agent." not in intro
    assert "The fourth agent." in intro

    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3],
        messages=[],
        speaker_selection_method="round_robin",
        max_round=10,
        send_introductions=True,
    )

    group_chat_manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=False,
        is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    )

    group_chat_manager.initiate_chat(group_chat_manager, message="The initiating message.")
    for a in [agent1, agent2, agent3]:
        messages = agent1.chat_messages[group_chat_manager]
        assert len(messages) == 3
        assert "The first agent." in messages[0]["content"]
        assert "The second agent." in messages[0]["content"]
        assert "The third agent." in messages[0]["content"]
        assert "The initiating message." == messages[1]["content"]
        assert messages[2]["content"] == agent1._default_auto_reply

    # Reset and start again
    agent1.reset()
    agent2.reset()
    agent3.reset()
    agent4.reset()

    # Check the default (no introductions)
    groupchat2 = autogen.GroupChat(
        agents=[agent1, agent2, agent3], messages=[], speaker_selection_method="round_robin", max_round=10
    )

    group_chat_manager2 = autogen.GroupChatManager(
        groupchat=groupchat2,
        llm_config=False,
        is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    )

    group_chat_manager2.initiate_chat(group_chat_manager2, message="The initiating message.")
    for a in [agent1, agent2, agent3]:
        messages = agent1.chat_messages[group_chat_manager2]
        assert len(messages) == 2
        assert "The initiating message." == messages[0]["content"]
        assert messages[1]["content"] == agent1._default_auto_reply


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


def test_init_default_parameters():
    agents = [autogen.ConversableAgent(name=f"Agent{i}", llm_config=False) for i in range(3)]
    group_chat = GroupChat(agents=agents, messages=[], max_round=3)
    for agent in agents:
        assert set([a.name for a in group_chat.allowed_speaker_transitions_dict[agent]]) == set(
            [a.name for a in agents]
        )


def test_graph_parameters():
    agents = [autogen.ConversableAgent(name=f"Agent{i}", llm_config=False) for i in range(3)]
    with pytest.raises(ValueError):
        GroupChat(
            agents=agents,
            messages=[],
            max_round=3,
            allowed_or_disallowed_speaker_transitions={agents[0]: [agents[1]], agents[1]: [agents[2]]},
        )
    with pytest.raises(ValueError):
        GroupChat(
            agents=agents,
            messages=[],
            max_round=3,
            allow_repeat_speaker=False,  # should be None
            allowed_or_disallowed_speaker_transitions={agents[0]: [agents[1]], agents[1]: [agents[2]]},
        )

    with pytest.raises(ValueError):
        GroupChat(
            agents=agents,
            messages=[],
            max_round=3,
            allow_repeat_speaker=None,
            allowed_or_disallowed_speaker_transitions={agents[0]: [agents[1]], agents[1]: [agents[2]]},
            speaker_transitions_type="a",
        )

    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=3,
        allowed_or_disallowed_speaker_transitions={agents[0]: [agents[1]], agents[1]: [agents[2]]},
        speaker_transitions_type="allowed",
    )
    assert "Agent0" in group_chat.agent_names


def test_graceful_exit_before_max_round():
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

    # This speaker_transitions limits the transition to be only from agent1 to agent2, and from agent2 to agent3 and end.
    allowed_or_disallowed_speaker_transitions = {agent1: [agent2], agent2: [agent3]}

    # Test empty is_termination_msg function
    groupchat = autogen.GroupChat(
        agents=[agent1, agent2, agent3],
        messages=[],
        speaker_selection_method="round_robin",
        max_round=10,
        allow_repeat_speaker=None,
        allowed_or_disallowed_speaker_transitions=allowed_or_disallowed_speaker_transitions,
        speaker_transitions_type="allowed",
    )

    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False, is_termination_msg=None)

    agent1.initiate_chat(group_chat_manager, message="'None' is_termination_msg function.")

    # Note that 3 is much lower than 10 (max_round), so the conversation should end before 10 rounds.
    assert len(groupchat.messages) == 3


def test_clear_agents_history():
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
        human_input_mode="ALWAYS",
        llm_config=False,
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2, agent3], messages=[], max_round=3, enable_clear_history=True)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)

    # testing pure "clear history" statement
    with mock.patch.object(builtins, "input", lambda _: "clear history. How you doing?"):
        res = agent1.initiate_chat(group_chat_manager, message="hello", summary_method="last_msg")
    agent1_history = list(agent1._oai_messages.values())[0]
    agent2_history = list(agent2._oai_messages.values())[0]
    assert agent1_history == [{"content": "How you doing?", "name": "sam", "role": "user"}]
    assert agent2_history == [{"content": "How you doing?", "name": "sam", "role": "user"}]
    assert groupchat.messages == [{"content": "How you doing?", "name": "sam", "role": "user"}]
    print("Chat summary", res.summary)
    print("Chat cost", res.cost)
    print("Chat history", res.chat_history)

    # testing clear history for defined agent
    with mock.patch.object(builtins, "input", lambda _: "clear history bob. How you doing?"):
        agent1.initiate_chat(group_chat_manager, message="hello")
    agent1_history = list(agent1._oai_messages.values())[0]
    agent2_history = list(agent2._oai_messages.values())[0]
    assert agent1_history == [
        {"content": "hello", "role": "assistant"},
        {"content": "This is bob speaking.", "name": "bob", "role": "user"},
        {"content": "How you doing?", "name": "sam", "role": "user"},
    ]
    assert agent2_history == [{"content": "How you doing?", "name": "sam", "role": "user"}]
    assert groupchat.messages == [
        {"content": "hello", "role": "user", "name": "alice"},
        {"content": "This is bob speaking.", "name": "bob", "role": "user"},
        {"content": "How you doing?", "name": "sam", "role": "user"},
    ]

    # testing clear history with defined nr of messages to preserve
    with mock.patch.object(builtins, "input", lambda _: "clear history 1. How you doing?"):
        agent1.initiate_chat(group_chat_manager, message="hello")
    agent1_history = list(agent1._oai_messages.values())[0]
    agent2_history = list(agent2._oai_messages.values())[0]
    assert agent1_history == [
        {"content": "This is bob speaking.", "name": "bob", "role": "user"},
        {"content": "How you doing?", "name": "sam", "role": "user"},
    ]
    assert agent2_history == [
        {"content": "This is bob speaking.", "role": "assistant"},
        {"content": "How you doing?", "name": "sam", "role": "user"},
    ]
    assert groupchat.messages == [
        {"content": "This is bob speaking.", "role": "user", "name": "bob"},
        {"content": "How you doing?", "role": "user", "name": "sam"},
    ]

    # testing clear history with defined agent and nr of messages to preserve
    with mock.patch.object(builtins, "input", lambda _: "clear history bob 1. How you doing?"):
        agent1.initiate_chat(group_chat_manager, message="hello")
    agent1_history = list(agent1._oai_messages.values())[0]
    agent2_history = list(agent2._oai_messages.values())[0]
    assert agent1_history == [
        {"content": "hello", "role": "assistant"},
        {"content": "This is bob speaking.", "name": "bob", "role": "user"},
        {"content": "How you doing?", "name": "sam", "role": "user"},
    ]
    assert agent2_history == [
        {"content": "This is bob speaking.", "role": "assistant"},
        {"content": "How you doing?", "name": "sam", "role": "user"},
    ]
    assert groupchat.messages == [
        {"content": "hello", "name": "alice", "role": "user"},
        {"content": "This is bob speaking.", "name": "bob", "role": "user"},
        {"content": "How you doing?", "name": "sam", "role": "user"},
    ]


def test_get_agent_by_name():
    def agent(name: str) -> autogen.ConversableAgent:
        return autogen.ConversableAgent(
            name=name,
            max_consecutive_auto_reply=10,
            human_input_mode="NEVER",
            llm_config=False,
        )

    def team(members: List[autogen.Agent], name: str) -> autogen.Agent:
        gc = autogen.GroupChat(agents=members, messages=[])

        return autogen.GroupChatManager(groupchat=gc, name=name, llm_config=False)

    team_member1 = agent("team1_member1")
    team_member2 = agent("team1_member2")
    team_dup_member1 = agent("team1_member1")
    team_dup_member2 = agent("team1_member2")

    user = agent("user")
    team1 = team([team_member1, team_member2], "team1")
    team1_duplicate = team([team_dup_member1, team_dup_member2], "team1")

    gc = autogen.GroupChat(agents=[user, team1, team1_duplicate], messages=[])

    # Testing default arguments
    assert gc.agent_by_name("user") == user
    assert gc.agent_by_name("team1") == team1 or gc.agent_by_name("team1") == team1_duplicate

    # Testing recursive search
    assert gc.agent_by_name("user", recursive=True) == user
    assert (
        gc.agent_by_name("team1_member1", recursive=True) == team_member1
        or gc.agent_by_name("team1_member1", recursive=True) == team_dup_member1
    )

    # Get agent that does not exist
    assert gc.agent_by_name("team2") is None
    assert gc.agent_by_name("team2", recursive=True) is None
    assert gc.agent_by_name("team2", raise_on_name_conflict=True) is None
    assert gc.agent_by_name("team2", recursive=True, raise_on_name_conflict=True) is None

    # Testing naming conflict
    with pytest.raises(AgentNameConflict):
        gc.agent_by_name("team1", raise_on_name_conflict=True)

    # Testing name conflict with recursive search
    with pytest.raises(AgentNameConflict):
        gc.agent_by_name("team1_member1", recursive=True, raise_on_name_conflict=True)


def test_get_nested_agents_in_groupchat():
    def agent(name: str) -> autogen.ConversableAgent:
        return autogen.ConversableAgent(
            name=name,
            max_consecutive_auto_reply=10,
            human_input_mode="NEVER",
            llm_config=False,
        )

    def team(name: str) -> autogen.ConversableAgent:
        member1 = agent(f"member1_{name}")
        member2 = agent(f"member2_{name}")

        gc = autogen.GroupChat(agents=[member1, member2], messages=[])

        return autogen.GroupChatManager(groupchat=gc, name=name, llm_config=False)

    user = agent("user")
    team1 = team("team1")
    team2 = team("team2")

    gc = autogen.GroupChat(agents=[user, team1, team2], messages=[])

    agents = gc.nested_agents()
    assert len(agents) == 7


def test_nested_teams_chat():
    """Tests chat capabilities of nested teams"""
    team1_msg = {"content": "Hello from team 1"}
    team2_msg = {"content": "Hello from team 2"}

    def agent(name: str, auto_reply: Optional[Dict[str, Any]] = None) -> autogen.ConversableAgent:
        return autogen.ConversableAgent(
            name=name,
            max_consecutive_auto_reply=10,
            human_input_mode="NEVER",
            llm_config=False,
            default_auto_reply=auto_reply,
        )

    def team(name: str, auto_reply: Optional[Dict[str, Any]] = None) -> autogen.ConversableAgent:
        member1 = agent(f"member1_{name}", auto_reply=auto_reply)
        member2 = agent(f"member2_{name}", auto_reply=auto_reply)

        gc = autogen.GroupChat(agents=[member1, member2], messages=[])

        return autogen.GroupChatManager(groupchat=gc, name=name, llm_config=False)

    def chat(gc_manager: autogen.GroupChatManager):
        team1_member1 = gc_manager.groupchat.agent_by_name("member1_team1", recursive=True)
        team2_member2 = gc_manager.groupchat.agent_by_name("member2_team2", recursive=True)

        assert team1_member1 is not None
        assert team2_member2 is not None

        team1_member1.send(team1_msg, team2_member2, request_reply=True)

    user = agent("user")
    team1 = team("team1", auto_reply=team1_msg)
    team2 = team("team2", auto_reply=team2_msg)

    gc = autogen.GroupChat(agents=[user, team1, team2], messages=[])
    gc_manager = autogen.GroupChatManager(groupchat=gc, llm_config=False)

    chat(gc_manager)

    team1_member1 = gc.agent_by_name("member1_team1", recursive=True)
    team2_member2 = gc.agent_by_name("member2_team2", recursive=True)

    assert team1_member1 and team2_member2

    msg = team1_member1.chat_messages[team2_member2][0]
    reply = team1_member1.chat_messages[team2_member2][1]

    assert msg["content"] == team1_msg["content"]
    assert reply["content"] == team2_msg["content"]


if __name__ == "__main__":
    # test_func_call_groupchat()
    # test_broadcast()
    # test_chat_manager()
    # test_plugin()
    # test_speaker_selection_method()
    # test_n_agents_less_than_3()
    # test_agent_mentions()
    # test_termination()
    # test_next_agent()
    test_send_intros()
    # test_invalid_allow_repeat_speaker()
    # test_graceful_exit_before_max_round()
    # test_clear_agents_history()
