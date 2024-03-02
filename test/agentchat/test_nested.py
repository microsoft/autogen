#!/usr/bin/env python3 -m pytest

import pytest
import sys
import os
import autogen

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_nested():
    config_list = autogen.config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    llm_config = {"config_list": config_list}

    tasks = [
        """What's Microsoft's Stock price today?""",
        """Make a pleasant joke about it.""",
    ]

    inner_assistant = autogen.AssistantAgent(
        "Inner-assistant",
        llm_config=llm_config,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    inner_code_interpreter = autogen.UserProxyAgent(
        "Inner-code-interpreter",
        human_input_mode="NEVER",
        code_execution_config={
            "work_dir": "coding",
            "use_docker": False,
        },
        default_auto_reply="",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    groupchat = autogen.GroupChat(
        agents=[inner_assistant, inner_code_interpreter],
        messages=[],
        speaker_selection_method="round_robin",  # With two agents, this is equivalent to a 1:1 conversation.
        allow_repeat_speaker=False,
        max_round=8,
    )

    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        code_execution_config={
            "work_dir": "coding",
            "use_docker": False,
        },
    )

    assistant = autogen.AssistantAgent(
        name="Assistant",
        llm_config={"config_list": config_list},
        # is_termination_msg=lambda x: x.get("content", "") == "",
    )

    user = autogen.UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    writer = autogen.AssistantAgent(
        name="Writer",
        llm_config={"config_list": config_list},
        system_message="""
        You are a professional writer, known for
        your insightful and engaging articles.
        You transform complex concepts into compelling narratives.
        Reply "TERMINATE" in the end when everything is done.
        """,
    )

    reviewer = autogen.AssistantAgent(
        name="Reviewer",
        llm_config={"config_list": config_list},
        system_message="""
        You are a compliance reviewer, known for your thoroughness and commitment to standards.
        Your task is to scrutinize content for any harmful elements or regulatory violations, ensuring
        all materials align with required guidelines.
        You must review carefully, identify potential issues, and maintain the integrity of the organization.
        Your role demands fairness, a deep understanding of regulations, and a focus on protecting against
        harm while upholding a culture of responsibility.
        You also help make revisions to ensure the content is accurate, clear, and compliant.
        Reply "TERMINATE" in the end when everything is done.
        """,
    )

    def writing_message(recipient, messages, sender, config):
        return f"Polish the content to make an engaging and nicely formatted blog post. \n\n {recipient.chat_messages_for_summary(sender)[-1]['content']}"

    nested_chat_queue = [
        {"recipient": manager, "summary_method": "reflection_with_llm"},
        {"recipient": writer, "message": writing_message, "summary_method": "last_msg", "max_turns": 1},
        {
            "recipient": reviewer,
            "message": "Review the content provided.",
            "summary_method": "last_msg",
            "max_turns": 1,
        },
    ]
    assistant.register_nested_chats(
        nested_chat_queue,
        trigger=user,
    )
    user.initiate_chats([{"recipient": assistant, "message": tasks[0]}, {"recipient": assistant, "message": tasks[1]}])


if __name__ == "__main__":
    test_nested()
