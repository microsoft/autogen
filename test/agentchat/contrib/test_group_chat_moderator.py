import pytest
import autogen

from autogen.agentchat.contrib.group_chat_moderator import GroupChatModerator


def test_moderation_prompt():
    agent1 = autogen.ConversableAgent(
        "alice",
        system_message="You are Alice, a helpful AI assistant.",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice speaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        description="You are Bob, a helpful AI assistant.",
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
    agents = [agent1, agent2, agent3]
    groupchat = GroupChatModerator(agents=agents, messages=[], max_round=2)

    system_prompt = groupchat.select_speaker_msg(agents)

    # Make sure it contains the text we expect.
    assert (
        "Read the following conversation, then carefully consider who should speak next based on who's input would be most valued in this moment (e.g., to make the most progress on the task)."
        in system_prompt
    )

    # Make sure expected prompt or descriptions are present.
    assert "You are Alice, a helpful AI assistant." in system_prompt  # provided prompt
    assert "You are Bob, a helpful AI assistant." in system_prompt  # provided description
    assert "You are a helpful AI Assistant" in system_prompt  # default prompt

    selection_prompt = groupchat.select_speaker_prompt(agents)
    assert (
        "Read the above conversation, then carefully consider who should speak next based on who's input would be most valued in this moment to make progress on the task."
        in selection_prompt
    )
    assert "alice" in selection_prompt
    assert "bob" in selection_prompt
    assert "sam" in selection_prompt


if __name__ == "__main__":
    test_moderation_prompt()
