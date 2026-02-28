#!/usr/bin/env python3 -m pytest

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

import autogen
from autogen.agentchat.contrib.agent_builder import AgentBuilder

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from conftest import reason, skip_openai  # noqa: E402
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402  # noqa: E402

try:
    import chromadb
    import huggingface_hub
except ImportError:
    skip = True
else:
    skip = False

here = os.path.abspath(os.path.dirname(__file__))
llm_config = {"temperature": 0}


def _config_check(config):
    # check config loading
    assert config.get("coding", None) is not None
    assert config.get("default_llm_config", None) is not None
    assert config.get("code_execution_config", None) is not None

    for agent_config in config["agent_configs"]:
        assert agent_config.get("name", None) is not None
        assert agent_config.get("model", None) is not None
        assert agent_config.get("description", None) is not None
        assert agent_config.get("system_message", None) is not None


# Function initializes a group chat with agents and starts a execution_task.
def start_task(execution_task: str, agent_list: list):
    group_chat = autogen.GroupChat(agents=agent_list, messages=[], max_round=12)
    manager = autogen.GroupChatManager(
        groupchat=group_chat,
        llm_config={"config_list": autogen.config_list_from_json(f"{KEY_LOC}/{OAI_CONFIG_LIST}"), **llm_config},
    )

    agent_list[0].initiate_chat(manager, message=execution_task)


ask_ossinsight_mock = MagicMock()


# Function to test function calling
def ask_ossinsight(question: str) -> str:
    ask_ossinsight_mock(question)
    return "The repository microsoft/autogen has 123,456 stars on GitHub."


@pytest.mark.skipif(skip_openai, reason=reason)
def test_build():
    builder = AgentBuilder(
        config_file_or_env=OAI_CONFIG_LIST,
        config_file_location=KEY_LOC,
        builder_model=["gpt-4", "gpt-4-1106-preview"],
        agent_model=["gpt-4", "gpt-4-1106-preview"],
    )
    building_task = (
        "Find a paper on arxiv by programming, and analyze its application in some domain. "
        "For example, find a recent paper about gpt-4 on arxiv "
        "and find its potential applications in software."
    )
    agent_list, agent_config = builder.build(
        building_task=building_task,
        default_llm_config={"temperature": 0},
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
    )
    _config_check(agent_config)

    # check number of agents
    assert len(agent_config["agent_configs"]) <= builder.max_agents


@pytest.mark.skipif(skip_openai or skip, reason=reason + "OR dependency not installed")
def test_build_assistant_with_function_calling():
    list_of_functions = [
        {
            "name": "ossinsight_data_api",
            "description": "This is an API endpoint allowing users (analysts) to input question about GitHub in text format to retrieve the related and structured data.",
            "function": ask_ossinsight,
        }
    ]

    builder = AgentBuilder(
        config_file_or_env=OAI_CONFIG_LIST, config_file_location=KEY_LOC, builder_model="gpt-4", agent_model="gpt-4"
    )
    building_task = "How many stars microsoft/autogen has on GitHub?"

    agent_list, agent_config = builder.build(
        building_task=building_task,
        default_llm_config={"temperature": 0},
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
        list_of_functions=list_of_functions,
    )

    _config_check(agent_config)

    # check number of agents
    assert len(agent_config["agent_configs"]) <= builder.max_agents

    # Mock the 'ask_ossinsight' function in the '_main_' module using a context manager.
    with patch(f"{__name__}.ask_ossinsight") as mocked_function:
        # Execute 'start_task' which should trigger 'ask_ossinsight' due to the given execution task.
        start_task(
            execution_task="How many stars microsoft/autogen has on GitHub?",
            agent_list=agent_list,
        )

        # Verify that 'ask_ossinsight' was called exactly once during the task execution.
        mocked_function.assert_called()


@pytest.mark.skipif(
    skip_openai,
    reason="requested to skip",
)
def test_build_gpt_assistant_with_function_calling():
    list_of_functions = [
        {
            "name": "ossinsight_data_api",
            "description": "This is an API endpoint allowing users (analysts) to input question about GitHub in text format to retrieve the related and structured data.",
            "function": ask_ossinsight,
        }
    ]

    builder = AgentBuilder(
        config_file_or_env=OAI_CONFIG_LIST, config_file_location=KEY_LOC, builder_model="gpt-4", agent_model="gpt-4"
    )

    building_task = "Determine number of stars of GitHub repositories"

    agent_list, agent_config = builder.build(
        building_task=building_task,
        default_llm_config={"temperature": 0},
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
        list_of_functions=list_of_functions,
        use_oai_assistant=True,
    )

    _config_check(agent_config)

    # check number of agents
    assert len(agent_config["agent_configs"]) <= builder.max_agents

    # Mock the 'ask_ossinsight' function in the '_main_' module using a context manager.
    with patch(f"{__name__}.ask_ossinsight") as mocked_function:
        # Execute 'start_task' which should trigger 'ask_ossinsight' due to the given execution task.
        start_task(
            execution_task="How many stars microsoft/autogen has on GitHub?",
            agent_list=agent_list,
        )

        # Verify that 'ask_ossinsight' was called exactly once during the task execution.
        mocked_function.assert_called()


@pytest.mark.skipif(
    skip_openai or skip,
    reason=reason + "OR dependency not installed",
)
def test_build_from_library():
    builder = AgentBuilder(
        config_file_or_env=OAI_CONFIG_LIST,
        config_file_location=KEY_LOC,
        builder_model=["gpt-4", "gpt-4-1106-preview"],
        agent_model=["gpt-4", "gpt-4-1106-preview"],
    )
    building_task = (
        "Find a paper on arxiv by programming, and analyze its application in some domain. "
        "For example, find a recent paper about gpt-4 on arxiv "
        "and find its potential applications in software."
    )
    agent_list, agent_config = builder.build_from_library(
        building_task=building_task,
        library_path_or_json=f"{here}/example_agent_builder_library.json",
        default_llm_config={"temperature": 0},
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
    )
    _config_check(agent_config)

    # check number of agents
    assert len(agent_config["agent_configs"]) <= builder.max_agents

    builder.clear_all_agents()

    # test embedding similarity selection
    agent_list, agent_config = builder.build_from_library(
        building_task=building_task,
        library_path_or_json=f"{here}/example_agent_builder_library.json",
        default_llm_config={"temperature": 0},
        embedding_model="all-mpnet-base-v2",
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
    )
    _config_check(agent_config)

    # check number of agents
    assert len(agent_config["agent_configs"]) <= builder.max_agents


@pytest.mark.skipif(skip_openai, reason=reason)
def test_save():
    builder = AgentBuilder(
        config_file_or_env=OAI_CONFIG_LIST,
        config_file_location=KEY_LOC,
        builder_model=["gpt-4", "gpt-4-1106-preview"],
        agent_model=["gpt-4", "gpt-4-1106-preview"],
    )
    building_task = (
        "Find a paper on arxiv by programming, and analyze its application in some domain. "
        "For example, find a recent paper about gpt-4 on arxiv "
        "and find its potential applications in software."
    )

    builder.build(
        building_task=building_task,
        default_llm_config={"temperature": 0},
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
    )
    saved_files = builder.save(f"{here}/example_save_agent_builder_config.json")

    # check config file path
    assert os.path.isfile(saved_files)

    saved_configs = json.load(open(saved_files))

    _config_check(saved_configs)


@pytest.mark.skipif(skip_openai, reason=reason)
def test_load():
    builder = AgentBuilder(
        config_file_or_env=OAI_CONFIG_LIST,
        config_file_location=KEY_LOC,
        builder_model=["gpt-4", "gpt-4-1106-preview"],
        agent_model=["gpt-4", "gpt-4-1106-preview"],
    )

    config_save_path = f"{here}/example_test_agent_builder_config.json"
    json.load(open(config_save_path, "r"))

    agent_list, loaded_agent_configs = builder.load(
        config_save_path,
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
    )
    print(loaded_agent_configs)

    _config_check(loaded_agent_configs)


@pytest.mark.skipif(skip_openai, reason=reason)
def test_clear_agent():
    builder = AgentBuilder(
        config_file_or_env=OAI_CONFIG_LIST,
        config_file_location=KEY_LOC,
        builder_model=["gpt-4", "gpt-4-1106-preview"],
        agent_model=["gpt-4", "gpt-4-1106-preview"],
    )

    config_save_path = f"{here}/example_test_agent_builder_config.json"
    builder.load(
        config_save_path,
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
    )
    builder.clear_all_agents()

    # check if the agent cleared
    assert len(builder.agent_procs_assign) == 0


def test_multi_function_system_message_preserved():
    """Regression test for https://github.com/microsoft/autogen/issues/5037

    When multiple functions are registered to a single agent, the system message
    must accumulate ALL function descriptions and preserve the GROUP_CHAT_DESCRIPTION
    wrapper (including TERMINATE instructions). Before the fix, each iteration
    overwrote the system message from the static agent_configs dict, losing all
    previously registered functions and the GROUP_CHAT_DESCRIPTION.
    """
    # --- Setup: fake config list so AgentBuilder.__init__ doesn't need real API keys ---
    fake_config_list = [{"model": "gpt-4", "api_key": "fake-key-for-testing"}]

    with patch("autogen.config_list_from_json", return_value=fake_config_list):
        builder = AgentBuilder(
            config_file_or_env="FAKE_CONFIG",
            builder_model="gpt-4",
            agent_model="gpt-4",
        )

    # --- Populate cached_configs as build() would ---
    builder.cached_configs = {
        "building_task": "Test task for regression",
        "agent_configs": [
            {
                "name": "Test_Agent",
                "model": ["gpt-4"],
                "tags": [],
                "system_message": "You are a test agent that handles multiple tools.",
                "description": "A test agent for function registration.",
            },
        ],
        "coding": True,
        "default_llm_config": {"temperature": 0, "config_list": fake_config_list},
        "code_execution_config": {
            "last_n_messages": 1,
            "work_dir": "test_groupchat",
            "use_docker": False,
            "timeout": 10,
        },
    }

    # --- Define 3 dummy functions to register to the same agent ---
    def send_email(to: str, body: str) -> str:
        return "sent"

    def get_user_email(user_id: str) -> str:
        return "user@example.com"

    def open_browser(url: str) -> str:
        return "opened"

    list_of_functions = [
        {"name": "send_email", "description": "Send an email to a recipient", "function": send_email},
        {"name": "get_user_email", "description": "Look up a user email address", "function": get_user_email},
        {"name": "open_browser", "description": "Open a URL in a web browser", "function": open_browser},
    ]

    # --- Mock builder_model.create to always assign functions to Test_Agent ---
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test_Agent"
    builder.builder_model = MagicMock()
    builder.builder_model.create.return_value = mock_response

    # --- Mock config_list_from_json for _create_agent's internal call ---
    with patch("autogen.config_list_from_json", return_value=fake_config_list):
        agent_list, cached_configs = builder._build_agents(
            use_oai_assistant=False,
            list_of_functions=list_of_functions,
        )

    # --- Find Test_Agent in the built agents ---
    test_agent = None
    for agent in agent_list:
        if agent.name == "Test_Agent":
            test_agent = agent
            break
    assert test_agent is not None, "Test_Agent not found in agent_list"

    sys_msg = test_agent.system_message

    # Verify ALL function descriptions are preserved (not just the last one)
    assert "send_email" in sys_msg, (
        f"send_email lost from system message after multi-function registration.\n"
        f"System message:\n{sys_msg}"
    )
    assert "Send an email to a recipient" in sys_msg, (
        "send_email description lost from system message"
    )
    assert "get_user_email" in sys_msg, (
        f"get_user_email lost from system message after multi-function registration.\n"
        f"System message:\n{sys_msg}"
    )
    assert "Look up a user email address" in sys_msg, (
        "get_user_email description lost from system message"
    )
    assert "open_browser" in sys_msg, (
        f"open_browser lost from system message after multi-function registration.\n"
        f"System message:\n{sys_msg}"
    )
    assert "Open a URL in a web browser" in sys_msg, (
        "open_browser description lost from system message"
    )

    # Verify GROUP_CHAT_DESCRIPTION wrapper is preserved (TERMINATE instruction)
    assert "TERMINATE" in sys_msg, (
        f"TERMINATE instruction lost from system message after function registration.\n"
        f"System message:\n{sys_msg}"
    )

    # Verify GROUP_CHAT_DESCRIPTION structural elements
    assert "Group chat instruction" in sys_msg, (
        "GROUP_CHAT_DESCRIPTION header lost from system message"
    )
    assert "Test_Agent" in sys_msg, (
        "Agent role name lost from GROUP_CHAT_DESCRIPTION"
    )


if __name__ == "__main__":
    test_build()
    test_build_assistant_with_function_calling()
    test_build_gpt_assistant_with_function_calling()
    test_build_from_library()
    test_save()
    test_load()
    test_clear_agent()
    test_multi_function_system_message_preserved()
