from pathlib import Path
import sys
import os
import tempfile
import uuid
import pytest
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.code_utils import is_docker_running
from autogen.coding.base import CodeBlock, CodeExecutor
from autogen.coding.factory import CodeExecutorFactory
from autogen.coding.docker_commandline_code_executor import DockerCommandLineCodeExecutor
from autogen.coding.local_commandline_code_executor import LocalCommandLineCodeExecutor

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import MOCK_OPEN_AI_API_KEY, skip_docker  # noqa: E402

if skip_docker or not is_docker_running():
    classes_to_test = [LocalCommandLineCodeExecutor]
else:
    classes_to_test = [LocalCommandLineCodeExecutor, DockerCommandLineCodeExecutor]

UNIX_SHELLS = ["bash", "sh", "shell"]
WINDOWS_SHELLS = ["ps1", "pwsh", "powershell"]


@pytest.mark.parametrize("cls", classes_to_test)
def test_is_code_executor(cls) -> None:
    assert isinstance(cls, CodeExecutor)


def test_create_local() -> None:
    config = {"executor": "commandline-local"}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, LocalCommandLineCodeExecutor)

    config = {"executor": LocalCommandLineCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert executor is config["executor"]


@pytest.mark.skipif(
    skip_docker or not is_docker_running(),
    reason="docker is not running or requested to skip docker tests",
)
def test_create_docker() -> None:
    config = {"executor": DockerCommandLineCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert executor is config["executor"]


@pytest.mark.parametrize("cls", classes_to_test)
def test_commandline_executor_init(cls) -> None:
    executor = cls(timeout=10, work_dir=".")
    assert executor.timeout == 10 and str(executor.work_dir) == "."

    # Try invalid working directory.
    with pytest.raises(FileNotFoundError):
        executor = cls(timeout=111, work_dir="/invalid/directory")


@pytest.mark.parametrize("cls", classes_to_test)
def test_commandline_executor_execute_code(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = cls(work_dir=temp_dir)
        _test_execute_code(executor=executor)


def _test_execute_code(executor: CodeExecutor) -> None:
    # Test single code block.
    code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

    # Test multiple code blocks.
    code_blocks = [
        CodeBlock(code="import sys; print('hello world!')", language="python"),
        CodeBlock(code="a = 100 + 100; print(a)", language="python"),
    ]
    code_result = executor.execute_code_blocks(code_blocks)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file is not None
    )

    # Test bash script.
    if sys.platform not in ["win32"]:
        code_blocks = [CodeBlock(code="echo 'hello world!'", language="bash")]
        code_result = executor.execute_code_blocks(code_blocks)
        assert code_result.exit_code == 0 and "hello world!" in code_result.output and code_result.code_file is not None

    # Test running code.
    file_lines = ["import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
    code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
        and code_result.code_file is not None
    )

    # Check saved code file.
    with open(code_result.code_file) as f:
        code_lines = f.readlines()
        for file_line, code_line in zip(file_lines, code_lines):
            assert file_line.strip() == code_line.strip()


@pytest.mark.parametrize("cls", classes_to_test)
def test_commandline_code_executor_timeout(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = cls(timeout=1, work_dir=temp_dir)
        _test_timeout(executor)


def _test_timeout(executor: CodeExecutor) -> None:
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code and "Timeout" in code_result.output


def test_local_commandline_code_executor_restart() -> None:
    executor = LocalCommandLineCodeExecutor()
    _test_restart(executor)


# This is kind of hard to test because each exec is a new env
@pytest.mark.skipif(
    skip_docker or not is_docker_running(),
    reason="docker is not running or requested to skip docker tests",
)
def test_docker_commandline_code_executor_restart() -> None:
    with DockerCommandLineCodeExecutor() as executor:
        result = executor.execute_code_blocks([CodeBlock(code="echo $HOME", language="sh")])
        assert result.exit_code == 0
        executor.restart()
        result = executor.execute_code_blocks([CodeBlock(code="echo $HOME", language="sh")])
        assert result.exit_code == 0


def _test_restart(executor: CodeExecutor) -> None:
    # Check warning.
    with pytest.warns(UserWarning, match=r".*No action is taken."):
        executor.restart()


@pytest.mark.parametrize("cls", classes_to_test)
def test_commandline_executor_conversable_agent_code_execution(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = cls(work_dir=temp_dir)
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("OPENAI_API_KEY", MOCK_OPEN_AI_API_KEY)
            _test_conversable_agent_code_execution(executor)


def _test_conversable_agent_code_execution(executor: CodeExecutor) -> None:
    agent = ConversableAgent(
        "user_proxy",
        code_execution_config={"executor": executor},
        llm_config=False,
    )

    assert agent.code_executor is executor

    message = """
    Example:
    ```python
    print("hello extract code")
    ```
    """

    reply = agent.generate_reply(
        [{"role": "user", "content": message}],
        sender=ConversableAgent("user", llm_config=False, code_execution_config=False),
    )
    assert "hello extract code" in reply  # type: ignore[operator]


# Test cases for dangerous commands that should be caught by the sanitizer
@pytest.mark.parametrize(
    "lang, code, expected_message",
    [
        ("bash", "rm -rf /", "Use of 'rm -rf' command is not allowed."),
        ("bash", "mv myFile /dev/null", "Moving files to /dev/null is not allowed."),
        ("bash", "dd if=/dev/zero of=/dev/sda", "Use of 'dd' command is not allowed."),
        ("bash", "echo Hello > /dev/sda", "Overwriting disk blocks directly is not allowed."),
        ("bash", ":(){ :|:& };:", "Fork bombs are not allowed."),
    ],
)
def test_dangerous_commands(lang, code, expected_message):
    with pytest.raises(ValueError) as exc_info:
        LocalCommandLineCodeExecutor.sanitize_command(lang, code)
    assert expected_message in str(
        exc_info.value
    ), f"Expected message '{expected_message}' not found in '{str(exc_info.value)}'"


@pytest.mark.parametrize("cls", classes_to_test)
def test_invalid_relative_path(cls) -> None:
    executor = cls()
    code = """# filename: /tmp/test.py

print("hello world")
"""
    result = executor.execute_code_blocks([CodeBlock(code=code, language="python")])
    assert result.exit_code == 1 and "Filename is not in the workspace" in result.output


@pytest.mark.parametrize("cls", classes_to_test)
def test_valid_relative_path(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        executor = cls(work_dir=temp_dir)
        code = """# filename: test.py

print("hello world")
"""
        result = executor.execute_code_blocks([CodeBlock(code=code, language="python")])
        assert result.exit_code == 0
        assert "hello world" in result.output
        assert "test.py" in result.code_file
        assert (temp_dir / "test.py").resolve() == Path(result.code_file).resolve()
        assert (temp_dir / "test.py").exists()


@pytest.mark.parametrize("cls", classes_to_test)
@pytest.mark.parametrize("lang", WINDOWS_SHELLS + UNIX_SHELLS)
def test_silent_pip_install(cls, lang: str) -> None:
    # Ensure that the shell is supported.
    lang = "ps1" if lang in ["powershell", "pwsh"] else lang

    if sys.platform in ["win32"] and lang in UNIX_SHELLS:
        pytest.skip("Linux shells are not supported on Windows.")
    elif sys.platform not in ["win32"] and lang in WINDOWS_SHELLS:
        pytest.skip("Windows shells are not supported on Unix.")

    error_exit_code = 0 if sys.platform in ["win32"] else 1

    executor = cls(timeout=600)

    code = "pip install matplotlib numpy"
    code_blocks = [CodeBlock(code=code, language=lang)]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and code_result.output.strip() == ""

    none_existing_package = uuid.uuid4().hex

    code = f"pip install matplotlib_{none_existing_package}"
    code_blocks = [CodeBlock(code=code, language=lang)]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == error_exit_code and "ERROR: " in code_result.output
