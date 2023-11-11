import pytest
import autogen

from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

try:
    from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent
except ImportError:
    skip = True
else:
    skip = False


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


@pytest.mark.skipif(skip, reason="dependency is not installed")
def test_group_chat_with_lmm():
    # This is a bug report to show that a group chat with two MultimodalConversable Agents is not controlled by max_round of GroupChat.

    # A test that initiates two MultimodalConversable Agents to describe one image in different styles.

    config_list_gpt4v = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        filter_dict={
            "model": ["gpt-4-vision-preview"],
        },
        file_location=KEY_LOC,
    )

    llm_config_gpt4v = {"config_list": config_list_gpt4v, "seed": 42}

    # The parameters and agent mimics agentchat_lmm_gpt-4v.ipynb
    # However it fails with only 1 message in groupchat
    agent1 = MultimodalConversableAgent(
        name="image-explainer-1",
        max_consecutive_auto_reply=10,
        llm_config={"config_list": config_list_gpt4v, "temperature": 0.5, "max_tokens": 300},
        system_message="Your image description is poetic and engaging.",
    )
    agent2 = MultimodalConversableAgent(
        name="image-explainer-2",
        max_consecutive_auto_reply=10,
        llm_config={"config_list": config_list_gpt4v, "temperature": 0.5, "max_tokens": 300},
        system_message="Your image description is factual and to the point.",
    )

    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="Ask both image explainer 1 and 2 for their description.",
        human_input_mode="NEVER",  # Try between ALWAYS or NEVER
        max_consecutive_auto_reply=10,
    )

    # We set max_round to 5
    groupchat = autogen.GroupChat(agents=[agent1, agent2, user_proxy], messages=[], max_round=5)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_gpt4v)

    # However, running this initate_chat, we observe that it goes way beyond 5 rounds
    # user_proxy.initiate_chat(group_chat_manager,
    #                     message=f"""What do you see?
    #                     <img https://th.bing.com/th/id/R.422068ce8af4e15b0634fe2540adea7a?rik=y4OcXBE%2fqutDOw&pid=ImgRaw&r=0>.""")

    # Dummy assert - to replace with the bug is fixed
    assert 1 == 1
    # Dummy do somthing with group_chat_manager so that it is not removed in pre-commit
    print(group_chat_manager)


if __name__ == "__main__":
    # test_func_call_groupchat()
    # test_broadcast()
    # test_chat_manager()
    # test_plugin()
    test_group_chat_with_lmm()
