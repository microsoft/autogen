#!/usr/bin/env python3 -m pytest

from autogen import AssistantAgent, UserProxyAgent
from autogen import GroupChat, GroupChatManager
import asyncio
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
import pytest
from conftest import skip_openai
import autogen
from typing import Literal
from typing_extensions import Annotated
from autogen import initiate_chats


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
@pytest.mark.asyncio
async def test_async_chats():
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        """Get their stock price.""",
        """Analyze pros and cons. Keep it short.""",
    ]

    writing_tasks = ["""Develop a short but engaging blog post using any information provided."""]

    financial_assistant_1 = AssistantAgent(
        name="Financial_assistant_1",
        llm_config={"config_list": config_list},
    )
    financial_assistant_2 = AssistantAgent(
        name="Financial_assistant_2",
        llm_config={"config_list": config_list},
    )
    writer = AssistantAgent(
        name="Writer",
        llm_config={"config_list": config_list},
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        system_message="""
            You are a professional writer, known for
            your insightful and engaging articles.
            You transform complex concepts into compelling narratives.
            Reply "TERMINATE" in the end when everything is done.
            """,
    )

    user = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    def my_summary_method(recipient, sender):
        return recipient.chat_messages[sender][0].get("content", "")

    chat_res = await user.a_initiate_chats(
        [
            {
                "chat_id": 1,
                "recipient": financial_assistant_1,
                "message": financial_tasks[0],
                "silent": False,
                "summary_method": my_summary_method,
            },
            {
                "chat_id": 2,
                "prerequisites": [1],
                "recipient": financial_assistant_2,
                "message": financial_tasks[1],
                "silent": True,
                "summary_method": "reflection_with_llm",
            },
            {
                "chat_id": 3,
                "prerequisites": [1, 2],
                "recipient": financial_assistant_1,
                "message": financial_tasks[2],
                "summary_method": "last_msg",
                "clear_history": False,
            },
            {
                "chat_id": 4,
                "prerequisites": [1, 2, 3],
                "recipient": writer,
                "message": writing_tasks[0],
                "carryover": "I want to include a figure or a table of data in the blogpost.",
                "summary_method": "last_msg",
            },
        ]
    )
    last_chat_id = 4

    chat_w_writer = chat_res[last_chat_id]
    print(chat_w_writer.chat_history, chat_w_writer.summary, chat_w_writer.cost)

    all_res = user.get_chat_results()
    writer_res = user.get_chat_results(last_chat_id)

    # print(blogpost.summary, insights_and_blogpost)
    print(writer_res.summary, writer_res.cost)

    print(all_res[1].human_input)
    print(all_res[1].summary)
    print(all_res[1].chat_history)
    print(all_res[2].summary)


if __name__ == "__main__":
    test_async_chats()
