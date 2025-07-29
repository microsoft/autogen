"""Tests for MagenticOne team."""

import os
import warnings
from unittest.mock import Mock, patch

import pytest
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_core.models import ChatCompletionClient
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.teams.magentic_one import MagenticOne


def docker_tests_enabled() -> bool:
    """Check if Docker tests should be enabled."""
    if os.environ.get("SKIP_DOCKER", "unset").lower() == "true":
        return False

    try:
        import docker
        from docker.errors import DockerException
    except ImportError:
        return False

    try:
        client = docker.from_env()
        client.ping()  # type: ignore
        return True
    except DockerException:
        return False


def _is_docker_available() -> bool:
    """Local implementation of Docker availability check."""
    return docker_tests_enabled()


@pytest.fixture
def mock_chat_client() -> Mock:
    """Create a mock chat completion client."""
    mock_client = Mock(spec=ChatCompletionClient)
    mock_client.model_info = {"function_calling": True, "json_output": True, "vision": True}
    return mock_client


@pytest.mark.skipif(not docker_tests_enabled(), reason="Docker is not available")
def test_magentic_one_uses_docker_by_default(mock_chat_client: Mock) -> None:
    """Test that MagenticOne uses Docker code executor by default when Docker is available."""
    from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)

        m1 = MagenticOne(client=mock_chat_client)

        # Find the CodeExecutorAgent in the participants list
        code_executor_agent = None
        for agent in m1._participants:  # type: ignore[reportPrivateUsage]
            if isinstance(agent, CodeExecutorAgent):
                code_executor_agent = agent
                break

        assert code_executor_agent is not None, "CodeExecutorAgent not found"
        assert isinstance(
            code_executor_agent._code_executor,  # type: ignore[reportPrivateUsage]
            DockerCommandLineCodeExecutor,  # type: ignore[reportPrivateUsage]
        ), f"Expected DockerCommandLineCodeExecutor, got {type(code_executor_agent._code_executor)}"  # type: ignore[reportPrivateUsage]


def test_docker_availability_check() -> None:
    """Test the Docker availability check function."""
    # This test should pass regardless of Docker availability
    result = _is_docker_available()
    assert isinstance(result, bool)


@patch("autogen_ext.teams.magentic_one._is_docker_available")
def test_magentic_one_falls_back_to_local_when_docker_unavailable(
    mock_docker_check: Mock, mock_chat_client: Mock
) -> None:
    """Test that MagenticOne falls back to local executor when Docker is not available."""
    mock_docker_check.return_value = False

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        m1 = MagenticOne(client=mock_chat_client)

        # Find the CodeExecutorAgent in the participants list
        code_executor_agent = None
        for agent in m1._participants:  # type: ignore[reportPrivateUsage]
            if isinstance(agent, CodeExecutorAgent):
                code_executor_agent = agent
                break

        assert code_executor_agent is not None, "CodeExecutorAgent not found"
        assert isinstance(
            code_executor_agent._code_executor,  # type: ignore[reportPrivateUsage]
            LocalCommandLineCodeExecutor,  # type: ignore[reportPrivateUsage]
        ), f"Expected LocalCommandLineCodeExecutor, got {type(code_executor_agent._code_executor)}"  # type: ignore[reportPrivateUsage]

        # Check that appropriate warnings were issued
        warning_messages = [str(warning.message) for warning in w]
        docker_warning_found = any("Docker is not available" in msg for msg in warning_messages)
        deprecated_warning_found = any(
            "Instantiating MagenticOne without a code_executor is deprecated" in msg for msg in warning_messages
        )

        assert docker_warning_found, f"Docker unavailable warning not found in: {warning_messages}"
        assert deprecated_warning_found, f"Deprecation warning not found in: {warning_messages}"


def test_magentic_one_with_explicit_code_executor(mock_chat_client: Mock) -> None:
    """Test that MagenticOne uses the provided code executor when explicitly given."""
    explicit_executor = LocalCommandLineCodeExecutor()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        m1 = MagenticOne(client=mock_chat_client, code_executor=explicit_executor)

        # Find the CodeExecutorAgent in the participants list
        code_executor_agent = None
        for agent in m1._participants:  # type: ignore[reportPrivateUsage]
            if isinstance(agent, CodeExecutorAgent):
                code_executor_agent = agent
                break

        assert code_executor_agent is not None, "CodeExecutorAgent not found"
        assert code_executor_agent._code_executor is explicit_executor, "Expected the explicitly provided code executor"  # type: ignore[reportPrivateUsage]

        # No deprecation warning should be issued when explicitly providing a code executor
        warning_messages = [str(warning.message) for warning in w]
        deprecated_warning_found = any(
            "Instantiating MagenticOne without a code_executor is deprecated" in msg for msg in warning_messages
        )

        assert not deprecated_warning_found, f"Unexpected deprecation warning found: {warning_messages}"
