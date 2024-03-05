#!/usr/bin/env python3 -m pytest

from autogen import AssistantAgent, UserProxyAgent
from autogen import GroupChat, GroupChatManager
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
import pytest
import sys
import os
import autogen
from typing import Literal
from typing_extensions import Annotated
from autogen import initiate_chats

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402


def test_chat_messages_for_summary():
    assistant = UserProxyAgent(name="assistant", human_input_mode="NEVER")
    user = UserProxyAgent(name="user", human_input_mode="NEVER")
    user.send("What is the capital of France?", assistant)
    messages = assistant.chat_messages_for_summary(user)
    assert len(messages) == 1

    groupchat = GroupChat(agents=[user, assistant], messages=[], max_round=2)
    manager = GroupChatManager(groupchat=groupchat, name="manager", llm_config=False)
    user.initiate_chat(manager, message="What is the capital of France?")
    messages = manager.chat_messages_for_summary(user)
    assert len(messages) == 2

    messages = user.chat_messages_for_summary(manager)
    assert len(messages) == 2
    messages = assistant.chat_messages_for_summary(manager)
    assert len(messages) == 2


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_chats_group():
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )
    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        """Pros and cons of the companies I'm interested in. Keep it short.""",
    ]

    writing_tasks = ["""Develop a short but engaging blog post using any information provided."""]

    user_proxy = UserProxyAgent(
        name="User_proxy",
        system_message="A human admin.",
        human_input_mode="NEVER",
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "groupchat",
            "use_docker": False,
        },
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
    )

    financial_assistant = AssistantAgent(
        name="Financial_assistant",
        llm_config={"config_list": config_list},
    )

    writer = AssistantAgent(
        name="Writer",
        llm_config={"config_list": config_list},
        system_message="""
        You are a professional writer, known for
        your insightful and engaging articles.
        You transform complex concepts into compelling narratives.
        Reply "TERMINATE" in the end when everything is done.
        """,
    )

    critic = AssistantAgent(
        name="Critic",
        system_message="""Critic. Double check plan, claims, code from other agents and provide feedback. Check whether the plan includes adding verifiable info such as source URL.
        Reply "TERMINATE" in the end when everything is done.
        """,
        llm_config={"config_list": config_list},
    )

    groupchat_1 = GroupChat(agents=[user_proxy, financial_assistant, critic], messages=[], max_round=50)

    groupchat_2 = GroupChat(agents=[user_proxy, writer, critic], messages=[], max_round=50)

    manager_1 = GroupChatManager(
        groupchat=groupchat_1,
        name="Research_manager",
        llm_config={"config_list": config_list},
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "groupchat",
            "use_docker": False,
        },
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )
    manager_2 = GroupChatManager(
        groupchat=groupchat_2,
        name="Writing_manager",
        llm_config={"config_list": config_list},
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "groupchat",
            "use_docker": False,
        },
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
    )

    user = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )
    chat_res = user.initiate_chats(
        [
            {
                "recipient": financial_assistant,
                "message": financial_tasks[0],
                "summary_method": "last_msg",
            },
            {
                "recipient": manager_1,
                "message": financial_tasks[1],
                "summary_method": "reflection_with_llm",
            },
            {"recipient": manager_2, "message": writing_tasks[0]},
        ]
    )

    chat_w_manager = chat_res[-1]
    print(chat_w_manager.chat_history, chat_w_manager.summary, chat_w_manager.cost)

    manager_2_res = user.get_chat_results(-1)
    all_res = user.get_chat_results()
    print(manager_2_res.summary, manager_2_res.cost)
    print(all_res[0].human_input)
    print(all_res[1].summary)


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_chats():
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

    chat_res = user.initiate_chats(
        [
            {
                "recipient": financial_assistant_1,
                "message": financial_tasks[0],
                "silent": False,
                "summary_method": my_summary_method,
            },
            {
                "recipient": financial_assistant_2,
                "message": financial_tasks[1],
                "silent": False,
                "max_turns": 1,
                "summary_method": "reflection_with_llm",
            },
            {
                "recipient": financial_assistant_1,
                "message": financial_tasks[2],
                "summary_method": "last_msg",
                "clear_history": False,
            },
            {
                "recipient": writer,
                "message": writing_tasks[0],
                "carryover": "I want to include a figure or a table of data in the blogpost.",
                "summary_method": "last_msg",
            },
        ]
    )

    chat_w_writer = chat_res[-1]
    print(chat_w_writer.chat_history, chat_w_writer.summary, chat_w_writer.cost)

    writer_res = user.get_chat_results(-1)
    all_res = user.get_chat_results()
    print(writer_res.summary, writer_res.cost)
    print(all_res[0].human_input)
    print(all_res[0].summary)
    print(all_res[0].chat_history)
    print(all_res[1].summary)
    assert len(all_res[1].chat_history) <= 2
    # print(blogpost.summary, insights_and_blogpost)


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_chats_general():
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

    user_2 = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        max_consecutive_auto_reply=3,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    def my_summary_method(recipient, sender):
        return recipient.chat_messages[sender][0].get("content", "")

    chat_res = initiate_chats(
        [
            {
                "sender": user,
                "recipient": financial_assistant_1,
                "message": financial_tasks[0],
                "silent": False,
                "summary_method": my_summary_method,
            },
            {
                "sender": user_2,
                "recipient": financial_assistant_2,
                "message": financial_tasks[1],
                "silent": False,
                "max_turns": 3,
                "summary_method": "reflection_with_llm",
            },
            {
                "sender": user,
                "recipient": financial_assistant_1,
                "message": financial_tasks[2],
                "summary_method": "last_msg",
                "clear_history": False,
            },
            {
                "sender": user,
                "recipient": writer,
                "message": writing_tasks[0],
                "carryover": "I want to include a figure or a table of data in the blogpost.",
                "summary_method": "last_msg",
            },
        ]
    )

    chat_w_writer = chat_res[-1]
    print(chat_w_writer.chat_history, chat_w_writer.summary, chat_w_writer.cost)

    print(chat_res[0].human_input)
    print(chat_res[0].summary)
    print(chat_res[0].chat_history)
    print(chat_res[1].summary)
    assert len(chat_res[1].chat_history) <= 6
    # print(blogpost.summary, insights_and_blogpost)


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_chats_exceptions():
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        """Get their stock price.""",
        """Analyze pros and cons. Keep it short.""",
    ]

    financial_assistant_1 = AssistantAgent(
        name="Financial_assistant_1",
        llm_config={"config_list": config_list},
    )
    financial_assistant_2 = AssistantAgent(
        name="Financial_assistant_2",
        llm_config={"config_list": config_list},
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

    user_2 = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    with pytest.raises(
        AssertionError,
        match="summary_method must be a string chosen from 'reflection_with_llm' or 'last_msg' or a callable, or None.",
    ):
        user.initiate_chats(
            [
                {
                    "recipient": financial_assistant_1,
                    "message": financial_tasks[0],
                    "silent": False,
                    "summary_method": "last_msg",
                },
                {
                    "recipient": financial_assistant_2,
                    "message": financial_tasks[2],
                    "summary_method": "llm",
                    "clear_history": False,
                },
            ]
        )
    with pytest.raises(
        AssertionError,
        match="llm client must be set in either the recipient or sender when summary_method is reflection_with_llm.",
    ):
        user.initiate_chats(
            [
                {
                    "recipient": financial_assistant_1,
                    "message": financial_tasks[0],
                    "silent": False,
                    "summary_method": "last_msg",
                },
                {
                    "recipient": user_2,
                    "message": financial_tasks[2],
                    "clear_history": False,
                    "summary_method": "reflection_with_llm",
                },
            ]
        )


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_chats_w_func():
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    llm_config = {
        "config_list": config_list,
        "timeout": 120,
    }

    chatbot = autogen.AssistantAgent(
        name="chatbot",
        system_message="For currency exchange tasks, only use the functions you have been provided with. Reply TERMINATE when the task is done.",
        llm_config=llm_config,
    )

    # create a UserProxyAgent instance named "user_proxy"
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },
    )

    CurrencySymbol = Literal["USD", "EUR"]

    def exchange_rate(base_currency: CurrencySymbol, quote_currency: CurrencySymbol) -> float:
        if base_currency == quote_currency:
            return 1.0
        elif base_currency == "USD" and quote_currency == "EUR":
            return 1 / 1.1
        elif base_currency == "EUR" and quote_currency == "USD":
            return 1.1
        else:
            raise ValueError(f"Unknown currencies {base_currency}, {quote_currency}")

    @user_proxy.register_for_execution()
    @chatbot.register_for_llm(description="Currency exchange calculator.")
    def currency_calculator(
        base_amount: Annotated[float, "Amount of currency in base_currency"],
        base_currency: Annotated[CurrencySymbol, "Base currency"] = "USD",
        quote_currency: Annotated[CurrencySymbol, "Quote currency"] = "EUR",
    ) -> str:
        quote_amount = exchange_rate(base_currency, quote_currency) * base_amount
        return f"{quote_amount} {quote_currency}"

    res = user_proxy.initiate_chat(
        chatbot,
        message="How much is 123.45 USD in EUR?",
        summary_method="reflection_with_llm",
    )
    print(res.summary, res.cost, res.chat_history)


if __name__ == "__main__":
    test_chats()
    test_chats_general()
    # test_chats_exceptions()
    # test_chats_group()
    # test_chats_w_func()
    # test_chat_messages_for_summary()
