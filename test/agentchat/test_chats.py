from typing import Any, Dict, Optional, Tuple, Type, Union, get_args, Callable, List, Literal
from autogen import AssistantAgent, ConversableAgent, UserProxyAgent, config_list_from_json
from autogen import GroupChat, GroupChatManager


def test_groupchat():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

    financial_tasks = [
        """What are the full names of NVDA and TESLA, and what do they do for business.""",
        """Research the financial status of the companies I'm interested in.""",
    ]

    writing_tasks = [
        """Develop an engaging blog
            post using any information provided."""
    ]

    user_proxy = UserProxyAgent(
        name="User_proxy",
        system_message="A human admin.",
        # code_execution_config={"last_n_messages": 3, "work_dir": "groupchat"},
        human_input_mode="NEVER",
        code_execution_config={
            "last_n_messages": 1,
            "work_dir": "groupchat",
            "use_docker": False,
        },
    )

    financial_assistant = AssistantAgent(
        name="Financial_assistant",
        llm_config={"config_list": config_list},
        system_message="""
            You are a financial assistant. You are an expert in finance and investment.
            Reply "TERMINATE" in the end when everything is done.
            """,
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
    user.initiate_chats(
        [
            {"recipient": manager_1, "message": financial_tasks[0]},
            {"recipient": manager_2, "message": writing_tasks[0]},
        ]
    )


def test_chats():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

    financial_tasks = [
        """What are the full names of NVDA and TESLA, and what do they do for business.""",
        """Research the financial status of the companies I'm interested in.""",
    ]

    writing_tasks = [
        """Develop an engaging blog
            post using any information provided."""
    ]

    financial_assistant_1 = AssistantAgent(
        name="Financial_assistant_1",
        llm_config={"config_list": config_list},
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        system_message="""
            You are a financial research assistant.
            Reply "TERMINATE" in the end when everything is done.
            """,
    )
    financial_assistant_2 = AssistantAgent(
        name="Financial_assistant_2",
        llm_config={"config_list": config_list},
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        system_message="""
        You are a financial research assistant. You research about the business and financial status of companies.
        Reply "TERMINATE" in the end when everything is done.
        """,
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

    user.initiate_chats(
        [
            {
                "recipient": financial_assistant_1,
                "message": financial_tasks[0],
                "clear_history": True,
                "silent": False,
                "get_takeaway": "last_msg",
            },
            {
                "recipient": financial_assistant_2,
                "message": financial_tasks[1],
                "get_takeaway": "last_msg",
            },
            {
                "recipient": writer,
                "message": writing_tasks[0],
                "get_takeaway": "last_msg",
            },
        ]
    )


if __name__ == "__main__":
    test_chats()
    test_groupchat()
