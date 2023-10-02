import autogen


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


def test_function_call():
    import random

    def get_random_number():
        return random.randint(0, 100)

    config_list_gpt4 = autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
        filter_dict={
            "model": ["gpt-4", "gpt-4-0314", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
    )
    llm_config = {
        "config_list": config_list_gpt4,
        "seed": 42,
        "functions": [
            {
                "name": "get_random_number",
                "description": "Get a random number between 0 and 100",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ],
    }
    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human admin that will execute code.",
        function_map={"get_random_number": get_random_number},
        human_input_mode="NEVER",
    )
    coder = autogen.AssistantAgent(
        name="Player",
        system_message="You will can function 'get_random_number' to get a random number. Reply 'TERMINATE' when you get at least 1 even number and 1 odd number.",
        llm_config=llm_config,
    )
    groupchat = autogen.GroupChat(agents=[user_proxy, coder], messages=[], max_round=10)
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    user_proxy.initiate_chat(manager, message="Let's start the game!")


if __name__ == "__main__":
    # test_broadcast()
    # test_chat_manager()
    test_plugin()
    test_function_call()
