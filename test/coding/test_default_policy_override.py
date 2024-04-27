import pytest

from autogen.coding.docker_commandline_code_executor import DockerCommandLineCodeExecutor


def test_policy_override():
    default_policy = DockerCommandLineCodeExecutor.DEFAULT_EXECUTION_POLICY
    custom_policy = {
        "python": False,  # Change the default execution policy for Python
        "javascript": True,  # Change the default execution policy for JavaScript
    }

    executor = DockerCommandLineCodeExecutor(execution_policies=custom_policy)

    # Check if the default policies are overridden correctly
    assert not executor.execution_policies["python"], "Python execution should be disabled"
    assert executor.execution_policies["javascript"], "JavaScript execution should be enabled"

    # Ensure other languages still follow the default policy
    for lang, should_execute in default_policy.items():
        if lang not in custom_policy:
            assert executor.execution_policies[lang] == should_execute, f"Policy for {lang} should not be changed"

    # Check if only known languages are in the policies
    assert set(executor.execution_policies.keys()) == set(
        default_policy.keys()
    ), "Execution policies should only contain known languages"
