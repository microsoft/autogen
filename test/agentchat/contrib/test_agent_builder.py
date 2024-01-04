import pytest
import os
import json
import sys
from packaging.requirements import Requirement
from autogen.agentchat.contrib.agent_builder import AgentBuilder
from autogen import UserProxyAgent
from conftest import skip_openai

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
except ImportError:
    skip = True
else:
    skip = False or skip_openai


@pytest.mark.skipif(
    skip,
    reason="openai not installed OR requested to skip",
)
def test_build():
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

    # check number of agents
    assert len(builder.agent_procs_assign.keys()) <= builder.max_agents

    # check system message
    for agent, proc in builder.agent_procs_assign.values():
        assert "TERMINATE" in agent.system_message


@pytest.mark.skipif(
    skip,
    reason="openai not installed OR requested to skip",
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

    # check config format
    assert saved_configs.get("building_task", None) is not None
    assert saved_configs.get("agent_configs", None) is not None
    assert saved_configs.get("coding", None) is not None
    assert saved_configs.get("default_llm_config", None) is not None


@pytest.mark.skipif(
    skip,
    reason="openai not installed OR requested to skip",
)
def test_load():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")

    config_save_path = f"{here}/example_test_agent_builder_config.json"
    configs = json.load(open(config_save_path))
    agent_configs = {
        e["name"]: {"model": e["model"], "system_message": e["system_message"]} for e in configs["agent_configs"]
    }

    agent_list, loaded_agent_configs = builder.load(
        config_save_path,
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": f"{here}/test_agent_scripts",
            "timeout": 60,
            "use_docker": "python:3",
        },
    )

    # check config loading
    assert loaded_agent_configs["coding"] == configs["coding"]
    if loaded_agent_configs["coding"] is True:
        assert isinstance(agent_list[0], UserProxyAgent)
        agent_list = agent_list[1:]
    for agent in agent_list:
        agent_name = agent.name
        assert agent_configs.get(agent_name, None) is not None
        assert agent_configs[agent_name]["model"] == agent.llm_config["model"]
        assert agent_configs[agent_name]["system_message"] == agent.system_message


@pytest.mark.skipif(
    skip,
    reason="openai not installed OR requested to skip",
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
