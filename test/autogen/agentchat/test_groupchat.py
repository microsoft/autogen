from flaml import autogen


def test_chat_manager():
    group_chat_manager = autogen.GroupChatManager(max_round=2, llm_config=False)
    agent1 = autogen.GroupChatParticipant(
        "alice",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
        group_chat_manager=group_chat_manager,
    )
    agent2 = autogen.GroupChatParticipant(
        "bob",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
        group_chat_manager=group_chat_manager,
    )
    group_chat_manager.agents = [agent1, agent2]
    agent1.send("start", group_chat_manager)

    assert len(agent1.chat_messages[group_chat_manager.name]) == 2

    group_chat_manager.reset()
    agent1.reset()
    agent2.reset()
    agent2.send("start", group_chat_manager)


if __name__ == "__main__":
    # test_broadcast()
    test_chat_manager()
