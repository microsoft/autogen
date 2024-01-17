from autogen import UserProxyAgent
import pytest
from conftest import skip_openai
import os

from autogen.code_utils import (
    is_docker_running,
    in_docker_container,
)

try:
    import openai
except ImportError:
    skip = True
else:
    skip = False or skip_openai


def get_current_autogen_env_var():
    return os.environ.get("AUTOGEN_USE_DOCKER", None)


def restore_autogen_env_var(current_env_value):
    if current_env_value is None:
        del os.environ["AUTOGEN_USE_DOCKER"]
    else:
        os.environ["AUTOGEN_USE_DOCKER"] = current_env_value


def docker_running():
    return is_docker_running() or in_docker_container()


@pytest.mark.skipif(skip, reason="openai not installed")
def test_agent_setup_with_code_execution_off():
    user_proxy = UserProxyAgent(
        name="test_agent",
        human_input_mode="NEVER",
        code_execution_config=False,
    )

    assert user_proxy._code_execution_config is False


@pytest.mark.skipif(skip, reason="openai not installed")
def test_agent_setup_with_use_docker_false():
    user_proxy = UserProxyAgent(
        name="test_agent",
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False},
    )

    assert user_proxy._code_execution_config["use_docker"] is False


@pytest.mark.skipif(skip, reason="openai not installed")
def test_agent_setup_with_env_variable_false_and_docker_running():
    current_env_value = get_current_autogen_env_var()

    os.environ["AUTOGEN_USE_DOCKER"] = "False"
    user_proxy = UserProxyAgent(
        name="test_agent",
        human_input_mode="NEVER",
    )

    assert user_proxy._code_execution_config["use_docker"] is False

    restore_autogen_env_var(current_env_value)


@pytest.mark.skipif(skip or (not docker_running()), reason="openai not installed OR docker not running")
def test_agent_setup_with_default_and_docker_running():
    user_proxy = UserProxyAgent(
        name="test_agent",
        human_input_mode="NEVER",
    )

    assert user_proxy._code_execution_config["use_docker"] is True


@pytest.mark.skipif(skip or (docker_running()), reason="openai not installed OR docker running")
def test_raises_error_agent_setup_with_default_and_docker_not_running():
    with pytest.raises(RuntimeError):
        UserProxyAgent(
            name="test_agent",
            human_input_mode="NEVER",
        )


@pytest.mark.skipif(skip or (docker_running()), reason="openai not installed OR docker running")
def test_raises_error_agent_setup_with_env_variable_true_and_docker_not_running():
    current_env_value = get_current_autogen_env_var()

    os.environ["AUTOGEN_USE_DOCKER"] = "True"

    with pytest.raises(RuntimeError):
        UserProxyAgent(
            name="test_agent",
            human_input_mode="NEVER",
        )

    restore_autogen_env_var(current_env_value)


@pytest.mark.skipif(skip or (not docker_running()), reason="openai not installed OR docker not running")
def test_agent_setup_with_env_variable_true_and_docker_running():
    current_env_value = get_current_autogen_env_var()

    os.environ["AUTOGEN_USE_DOCKER"] = "True"

    user_proxy = UserProxyAgent(
        name="test_agent",
        human_input_mode="NEVER",
    )

    assert user_proxy._code_execution_config["use_docker"] is True

    restore_autogen_env_var(current_env_value)
