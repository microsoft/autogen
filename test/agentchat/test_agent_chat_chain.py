import autogen
from autogen.agentchat import AssistantAgent

OAI_CONFIG_LIST = "OAI_CONFIG_LIST"


def test_agent_chat_chain():
    conversations = {}
    autogen.ChatCompletion.start_logging(conversations)
    agent1 = AssistantAgent(
        "alice",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = AssistantAgent(
        "bob",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob sepaking.",
    )
    agent3 = AssistantAgent(
        "carol",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is carol sepaking.",
    )
    agent4 = AssistantAgent(
        "john",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is john sepaking.",
    )
    agent1.agent_chat_chain = [agent4, agent2, agent3]
    groupchat = autogen.GroupChat(agents=[agent1, agent2, agent3, agent4], messages=[], max_round=4)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent1.initiate_chat(group_chat_manager, message="This is alice sepaking.")
    assert (
        groupchat.messages[-1]["name"] == "carol"
        and groupchat.messages[-2]["name"] == "bob"
        and groupchat.messages[-3]["name"] == "john"
        and groupchat.messages[-4]["name"] == "alice"
    )


def test_no_agent_chat_chain():
    conversations = {}
    autogen.ChatCompletion.start_logging(conversations)
    agent1 = AssistantAgent(
        "alice",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = AssistantAgent(
        "bob",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob sepaking.",
    )
    agent3 = AssistantAgent(
        "carol",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is carol sepaking.",
    )
    agent4 = AssistantAgent(
        "john",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is john sepaking.",
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2, agent3, agent4], messages=[], max_round=4)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent1.initiate_chat(group_chat_manager, message="This is alice sepaking.")
    assert (
        groupchat.messages[-1]["name"] == "john"
        and groupchat.messages[-2]["name"] == "carol"
        and groupchat.messages[-3]["name"] == "bob"
        and groupchat.messages[-4]["name"] == "alice"
    )


if __name__ == "__main__":
    test_agent_chat_chain()
    test_no_agent_chat_chain()
