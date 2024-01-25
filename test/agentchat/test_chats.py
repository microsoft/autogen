from autogen import AssistantAgent, UserProxyAgent
from autogen import GroupChat, GroupChatManager
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
import pytest
from conftest import skip_openai
import autogen

try:
    import openai
except ImportError:
    skip = True
else:
    skip = False or skip_openai


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
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
    user.initiate_chats(
        [
            {
                "recipient": financial_assistant,
                "message": financial_tasks[0],
                "takeaway_method": "last_msg",
            },
            {
                "recipient": manager_1,
                "message": financial_tasks[1],
                "takeaway_method": "llm",
            },
            {"recipient": manager_2, "message": writing_tasks[0]},
        ]
    )


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
def test_chats():
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
    )

    financial_tasks = [
        """What are the full names of NVDA and TESLA.""",
        """Pros and cons of the companies I'm interested in. Keep it short.""",
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

    user.initiate_chats(
        [
            {
                "recipient": financial_assistant_1,
                "message": financial_tasks[0],
                "clear_history": True,
                "silent": False,
                "takeaway_method": "last_msg",
            },
            {
                "recipient": financial_assistant_2,
                "message": financial_tasks[1],
                "takeaway_method": "llm",
            },
            {
                "recipient": writer,
                "message": writing_tasks[0],
            },
        ]
    )


if __name__ == "__main__":
    test_chats()
    test_chats_group()
