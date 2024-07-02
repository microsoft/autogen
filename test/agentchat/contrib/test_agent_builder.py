#!/usr/bin/env python3 -m pytest

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
    with patch("test.agentchat.contrib.test_agent_builder.ask_ossinsight") as mocked_function:
        # Execute 'start_task' which should trigger 'ask_ossinsight' due to the given execution task.
        start_task(
            execution_task="How many stars microsoft/autogen has on GitHub?",
            agent_list=agent_list,
        )

        # Verify that 'ask_ossinsight' was called exactly once during the task execution.
        mocked_function.assert_called()


@pytest.mark.skipif(
    skip,
    reason="requested to skip",
)
def test_build_gpt_assistant_with_function_calling():
    ossinsight_api_schema = {
        "name": "ossinsight_data_api",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Enter your GitHub data question in the form of a clear and specific question to ensure the returned data is accurate and valuable. For optimal results, specify the desired format for the data table in your request.",
                }
            },
            "required": ["question"],
        },
        "description": "This is an API endpoint allowing users (analysts) to input question about GitHub in text format to retrieve the related and structured data.",
    }

    list_of_functions = [{"function_schema": ossinsight_api_schema, "function": ask_ossinsight}]

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
    with patch("_main_.ask_ossinsight") as mocked_function:
        # Execute 'start_task' which should trigger 'ask_ossinsight' due to the given execution task.
        start_task(
            execution_task="How many stars microsoft/autogen has on GitHub?",
            agent_list=agent_list,
        )

        # Verify that 'ask_ossinsight' was called exactly once during the task execution.
        mocked_function.assert_called()


@pytest.mark.skipif(
    skip,
    reason="requested to skip",
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


if __name__ == "__main__":
    test_build()
    test_build_assistant_with_function_calling()
    test_build_gpt_assistant_with_function_calling()
    test_build_from_library()
    test_save()
    test_load()
    test_clear_agent()
