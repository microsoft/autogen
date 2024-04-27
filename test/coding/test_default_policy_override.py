import pytest
from conftest import skip_docker

from autogen.code_utils import is_docker_running
from autogen.coding.docker_commandline_code_executor import DockerCommandLineCodeExecutor


@pytest.mark.skipif(
    skip_docker or not is_docker_running(), reason="Docker is not running or requested to skip Docker tests"
)
def test_policy_override():
    default_policy = DockerCommandLineCodeExecutor.DEFAULT_EXECUTION_POLICY
    custom_policy = {
        "python": False,
        "javascript": True,
    }

    executor = DockerCommandLineCodeExecutor(execution_policies=custom_policy)

    assert not executor.execution_policies["python"], "Python execution should be disabled"
    assert executor.execution_policies["javascript"], "JavaScript execution should be enabled"

    for lang, should_execute in default_policy.items():
        if lang not in custom_policy:
            assert executor.execution_policies[lang] == should_execute, f"Policy for {lang} should not be changed"

    assert set(executor.execution_policies.keys()) == set(
        default_policy.keys()
    ), "Execution policies should only contain known languages"
