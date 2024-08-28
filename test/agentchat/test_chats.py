#!/usr/bin/env python3 -m pytest

import os
import sys
from typing import Literal

import pytest
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
from typing_extensions import Annotated

import autogen
from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent, filter_config, initiate_chats
from autogen.agentchat.chat import _post_process_carryover_item

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import reason, skip_openai  # noqa: E402

config_list = (
    []
    if skip_openai
    else autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )
)

config_list_35 = (
    []
    if skip_openai
    else autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"tags": ["gpt-3.5-turbo"]},
    )
)

config_list_tool = filter_config(config_list_35, {"tags": ["tool"]})


def test_chat_messages_for_summary():
    assistant = UserProxyAgent(name="assistant", human_input_mode="NEVER", code_execution_config={"use_docker": False})
    user = UserProxyAgent(name="user", human_input_mode="NEVER", code_execution_config={"use_docker": False})
    user.send("What is the capital of France?", assistant)
    messages = assistant.chat_messages_for_summary(user)
    assert len(messages) == 1

    groupchat = GroupChat(agents=[user, assistant], messages=[], max_round=2)
    manager = GroupChatManager(
        groupchat=groupchat, name="manager", llm_config=False, code_execution_config={"use_docker": False}
    )
    user.initiate_chat(manager, message="What is the capital of France?")
    messages = manager.chat_messages_for_summary(user)
    assert len(messages) == 2

    messages = user.chat_messages_for_summary(manager)
    assert len(messages) == 2
    messages = assistant.chat_messages_for_summary(manager)
    assert len(messages) == 2


@pytest.mark.skipif(skip_openai, reason=reason)
def test_chats_group():
    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        """Give lucky numbers for them.""",
    ]

    writing_tasks = ["""Make a joke."""]

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
        llm_config={"config_list": config_list_35},
    )

    writer = AssistantAgent(
        name="Writer",
        llm_config={"config_list": config_list_35},
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
        llm_config={"config_list": config_list_35},
    )

    groupchat_1 = GroupChat(agents=[user_proxy, financial_assistant, critic], messages=[], max_round=3)

    groupchat_2 = GroupChat(agents=[user_proxy, writer, critic], messages=[], max_round=3)

    manager_1 = GroupChatManager(
        groupchat=groupchat_1,
        name="Research_manager",
        llm_config={"config_list": config_list_35},
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
        llm_config={"config_list": config_list_35},
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
                "max_turns": 1,
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


@pytest.mark.skipif(skip_openai, reason=reason)
def test_chats():
    import random

    class Function:
        call_count = 0

        def get_random_number(self):
            self.call_count += 1
            return random.randint(0, 100)

    def luck_number_message(sender, recipient, context):
        final_msg = {}
        final_msg["content"] = "Give lucky numbers for them."
        final_msg["function_call"] = {"name": "get_random_number", "arguments": "{}"}
        return final_msg

    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        luck_number_message,
        luck_number_message,
    ]

    writing_tasks = ["""Make a joke."""]

    func = Function()
    financial_assistant_1 = AssistantAgent(
        name="Financial_assistant_1",
        llm_config={"config_list": config_list_35},
        function_map={"get_random_number": func.get_random_number},
    )
    financial_assistant_2 = AssistantAgent(
        name="Financial_assistant_2",
        llm_config={"config_list": config_list_35},
        function_map={"get_random_number": func.get_random_number},
    )
    writer = AssistantAgent(
        name="Writer",
        llm_config={"config_list": config_list_35},
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

    def my_summary_method(recipient, sender, summary_args):
        return recipient.chat_messages[sender][1].get("content", "")

    # chat_res_play = user.initiate_chat(
    #     player,
    #     message= {"content": "Let's play a game.", "function_call": {"name": "get_random_number", "arguments": "{}"}},
    #     max_turns=1,
    #     summary_method=my_summary,
    #     summary_args={"prefix": "This is the last message:"},
    # )
    # print(chat_res_play.summary)

    chat_res = user.initiate_chats(
        [
            {
                "recipient": financial_assistant_1,
                "message": financial_tasks[0],
                "silent": False,
                "summary_method": my_summary_method,
                "verbose": True,
                "max_turns": 1,
            },
            {
                "recipient": financial_assistant_2,
                "message": financial_tasks[1],
                "silent": False,
                "max_turns": 1,
                "summary_method": "reflection_with_llm",
                "verbose": True,
            },
            {
                "recipient": financial_assistant_1,
                "message": financial_tasks[2],
                "summary_method": "last_msg",
                "clear_history": False,
                "max_turns": 1,
            },
            {
                "recipient": financial_assistant_1,
                "message": {
                    "content": "Let's play a game.",
                    "function_call": {"name": "get_random_number", "arguments": "{}"},
                },
                "carryover": "I like even number.",
                "summary_method": "last_msg",
                "max_turns": 1,
            },
            {
                "recipient": writer,
                "message": writing_tasks[0],
                "carryover": "Make the numbers relevant.",
                "summary_method": "last_msg",
                "max_turns": 1,
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


@pytest.mark.skipif(skip_openai, reason=reason)
def test_chats_general():
    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        """Give lucky numbers for them.""",
        """Give lucky words for them.""",
    ]

    writing_tasks = ["""Develop a short but engaging blog post using any information provided."""]

    financial_assistant_1 = AssistantAgent(
        name="Financial_assistant_1",
        llm_config={"config_list": config_list_35},
    )
    financial_assistant_2 = AssistantAgent(
        name="Financial_assistant_2",
        llm_config={"config_list": config_list_35},
    )
    writer = AssistantAgent(
        name="Writer",
        llm_config={"config_list": config_list_35},
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

    def my_summary_method(recipient, sender, summary_args):
        return recipient.chat_messages[sender][1].get("content", "")

    chat_res = initiate_chats(
        [
            {
                "sender": user,
                "recipient": financial_assistant_1,
                "message": financial_tasks[0],
                "silent": False,
                "summary_method": my_summary_method,
                "max_turns": 1,
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
                "max_turns": 1,
            },
            {
                "sender": user,
                "recipient": writer,
                "message": writing_tasks[0],
                "carryover": "I want to include a figure or a table of data in the blogpost.",
                "summary_method": "last_msg",
                "max_turns": 2,
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


@pytest.mark.skipif(skip_openai, reason=reason)
def test_chats_exceptions():
    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        """Give lucky numbers for them.""",
        """Give lucky words for them.""",
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
                    "max_turns": 1,
                },
                {
                    "recipient": financial_assistant_2,
                    "message": financial_tasks[2],
                    "summary_method": "llm",
                    "clear_history": False,
                    "max_turns": 1,
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
                    "max_turns": 1,
                },
                {
                    "recipient": user_2,
                    "message": financial_tasks[2],
                    "clear_history": False,
                    "summary_method": "reflection_with_llm",
                    "max_turns": 1,
                },
            ]
        )


@pytest.mark.skipif(skip_openai, reason=reason)
def test_chats_w_func():
    llm_config = {
        "config_list": config_list_tool,
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


@pytest.mark.skipif(skip_openai, reason=reason)
def test_udf_message_in_chats():
    llm_config_35 = {"config_list": config_list_35}

    research_task = """
    ## NVDA (NVIDIA Corporation)
    - Current Stock Price: $822.79
    - Performance over the past month: 24.36%

    ## TSLA (Tesla, Inc.)
    - Current Stock Price: $202.64
    - Performance over the past month: 7.84%

    Save them to a file named stock_prices.md.
    """

    def my_writing_task(sender, recipient, context):
        carryover = context.get("carryover", "")
        if isinstance(carryover, list):
            carryover = carryover[-1]

        try:
            filename = context.get("work_dir", "") + "/stock_prices.md"
            with open(filename, "r") as file:
                data = file.read()
        except Exception as e:
            data = f"An error occurred while reading the file: {e}"

        return """Make a joke. """ + "\nContext:\n" + carryover + "\nData:" + data

    researcher = autogen.AssistantAgent(
        name="Financial_researcher",
        llm_config=llm_config_35,
    )
    writer = autogen.AssistantAgent(
        name="Writer",
        llm_config=llm_config_35,
        system_message="""
            You are a professional writer, known for
            your insightful and engaging articles.
            You transform complex concepts into compelling narratives.
            Reply "TERMINATE" in the end when everything is done.
            """,
    )

    user_proxy_auto = autogen.UserProxyAgent(
        name="User_Proxy_Auto",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "tasks",
            "use_docker": False,
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )

    chat_results = autogen.initiate_chats(
        [
            {
                "sender": user_proxy_auto,
                "recipient": researcher,
                "message": research_task,
                "clear_history": True,
                "silent": False,
                "max_turns": 2,
            },
            {
                "sender": user_proxy_auto,
                "recipient": writer,
                "message": my_writing_task,
                "max_turns": 2,  # max number of turns for the conversation (added for demo purposes, generally not necessarily needed)
                "summary_method": "reflection_with_llm",
                "work_dir": "tasks",
            },
        ]
    )
    print(chat_results[0].summary, chat_results[0].cost)
    print(chat_results[1].summary, chat_results[1].cost)


def test_post_process_carryover_item():
    gemini_carryover_item = {"content": "How can I help you?", "role": "model"}
    assert (
        _post_process_carryover_item(gemini_carryover_item) == gemini_carryover_item["content"]
    ), "Incorrect carryover postprocessing"
    carryover_item = "How can I help you?"
    assert _post_process_carryover_item(carryover_item) == carryover_item, "Incorrect carryover postprocessing"


if __name__ == "__main__":
    test_chats()
    # test_chats_general()
    # test_chats_exceptions()
    # test_chats_group()
    # test_chats_w_func()
    # test_chat_messages_for_summary()
    # test_udf_message_in_chats()
    test_post_process_carryover_item()
