import pytest
import os
import json
import sys
from packaging.requirements import Requirement
from autogen.agentchat.contrib.agent_builder import AgentBuilder
from autogen import UserProxyAgent

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

here = os.path.abspath(os.path.dirname(__file__))
oai_config_path = OAI_CONFIG_LIST

# openai>=1 required
try:
    from openai import OpenAI, APIError
    from openai.types.chat import ChatCompletion
    from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
    from openai.types.completion import Completion
    from openai.types.completion_usage import CompletionUsage
    import diskcache

    OPENAI_INSTALLED = True
except ImportError:
    OPENAI_INSTALLED = False


def _config_check(config):
    # check config loading
    assert config.get("coding", None) is not None
    assert config.get("default_llm_config", None) is not None
    assert config.get("code_execution_config", None) is not None

    for agent_config in config["agent_configs"]:
        assert agent_config.get("name", None) is not None
        assert agent_config.get("model", None) is not None
        assert agent_config.get("system_message", None) is not None


@pytest.mark.skipif(
    not OPENAI_INSTALLED,
    reason="do not run when dependency is not installed",
)
def test_build():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")
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
    assert len(agent_list) <= builder.max_agents

    # check system message
    for cfg in agent_config["agent_configs"]:
        assert "TERMINATE" in cfg["system_message"]


@pytest.mark.skipif(
    not OPENAI_INSTALLED,
    reason="do not run when dependency is not installed",
)
def test_build_from_library():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4-1106-preview", agent_model="gpt-4")
    building_task = (
        "Find a paper on arxiv by programming, and analyze its application in some domain. "
        "For example, find a recent paper about gpt-4 on arxiv "
        "and find its potential applications in software."
    )
    agent_list, agent_config = builder.build_from_library(
        building_task=building_task,
        library_path=f"{here}/example_agent_builder_library.json",
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
    assert len(agent_list) <= builder.max_agents

    # check system message
    for cfg in agent_config["agent_configs"]:
        assert "TERMINATE" in cfg["system_message"]


@pytest.mark.skipif(
    not OPENAI_INSTALLED,
    reason="do not run when dependency is not installed",
)
def test_save():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")
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


@pytest.mark.skipif(
    not OPENAI_INSTALLED,
    reason="do not run when dependency is not installed",
)
def test_load():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")

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


@pytest.mark.skipif(
    not OPENAI_INSTALLED,
    reason="do not run when dependency is not installed",
)
def test_clear_agent():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")

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
