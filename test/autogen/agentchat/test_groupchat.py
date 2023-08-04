from flaml import autogen


def test_chat_manager():
    group_chat_manager = autogen.GroupChatManager(max_round=2, llm_config=False)
    agent1 = autogen.ResponsiveAgent(
        "alice",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = autogen.ResponsiveAgent(
        "bob",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
    )
    group_chat_manager.agents = [agent1, agent2]
    agent1.initiate_chat(group_chat_manager, message="hello")

    assert len(agent1.chat_messages[group_chat_manager]) == 2

    group_chat_manager.reset()
    agent1.reset()
    agent2.reset()
    agent2.initiate_chat(group_chat_manager, message="hello")


if __name__ == "__main__":
    # test_broadcast()
    test_chat_manager()
