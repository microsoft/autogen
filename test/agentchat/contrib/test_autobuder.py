import pytest
import os
import json
import sys
from autogen.agentchat.contrib.agent_builder import AgentBuilder

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

here = os.path.abspath(os.path.dirname(__file__))
oai_config_path = os.path.join(KEY_LOC, OAI_CONFIG_LIST)

try:
    import pkg_resources

    pkg_resources.require("openai>=1")
    import openai

    OPENAI_INSTALLED = True
except ImportError:
    OPENAI_INSTALLED = False


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or OPENAI_INSTALLED,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_build():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")
    building_task = (
        "Find a paper on arxiv by programming, and analysis its application in some domain. "
        "For example, find a latest paper about gpt-4 on arxiv "
        "and find its potential applications in software."
    )

    builder.build(
        building_task=building_task,
        default_llm_config={"temperature": 0},
        user_proxy_work_dir=f"{here}/test_agent_scripts",
        docker="python:3",
    )

    # check number of agents
    assert len(builder.agent_procs_assign.keys()) <= builder.max_agents

    # check system message
    for agent, proc in builder.agent_procs_assign.values():
        assert "TERMINATE" in agent.system_message


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or OPENAI_INSTALLED,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_save():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")
    building_task = (
        "Find a paper on arxiv by programming, and analysis its application in some domain. "
        "For example, find a latest paper about gpt-4 on arxiv "
        "and find its potential applications in software."
    )

    builder.build(
        building_task=building_task,
        default_llm_config={"temperature": 0},
        user_proxy_work_dir=f"{here}/test_agent_scripts",
        docker="python:3",
    )
    saved_files = builder.save(f"{here}/example_save_config.json")

    # check config file path
    assert os.path.isfile(saved_files)

    saved_configs = json.load(open(saved_files))

    # check config format
    assert saved_configs.get("building_task", None) is not None
    assert saved_configs.get("agent_configs", None) is not None
    assert saved_configs.get("manager_system_message", None) is not None
    assert saved_configs.get("coding", None) is not None
    assert saved_configs.get("default_llm_config", None) is not None


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or OPENAI_INSTALLED,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_load():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")

    config_save_path = f"{here}/example_test_config.json"
    configs = json.load(open(config_save_path))
    agent_configs = {
        e["name"]: {"model": e["model"], "system_message": e["system_message"]} for e in configs["agent_configs"]
    }

    builder.load(
        config_save_path,
        user_proxy_work_dir=f"{here}/test_agent_scripts",
        docker="python:3",
    )

    # check config loading
    assert builder.coding == configs["coding"]
    for agent in builder.agent_procs_assign.values():
        agent_name = agent[0].name
        assert agent_configs.get(agent_name, None) is not None
        assert agent_configs[agent_name]["model"] == agent[0].llm_config["model"]
        assert agent_configs[agent_name]["system_message"] == agent[0].system_message


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or OPENAI_INSTALLED,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_clear_agent():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")

    config_save_path = f"{here}/example_test_config.json"
    builder.load(
        config_save_path,
        user_proxy_work_dir=f"{here}/test_agent_scripts",
        docker="python:3",
    )
    builder.clear_all_agents()

    # check if the agent cleared
    assert len(builder.agent_procs_assign) == 0


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or OPENAI_INSTALLED,
    reason="do not run on MacOS or windows or dependency is not installed",
)
def test_start():
    builder = AgentBuilder(config_path=oai_config_path, builder_model="gpt-4", agent_model="gpt-4")
    config_save_path = f"{here}/example_test_config.json"
    builder.load(config_save_path)
    test_task = "Find a latest paper about gpt-4 on arxiv and find its potential applications in software."

    group_chat, _ = builder.start(task=test_task)
    history = group_chat.messages.copy()

    assert history[0]["content"] == test_task
    history.reverse()
    for msg in history:
        if msg["content"] != "":
            assert "TERMINATE" in msg["content"]
            break
