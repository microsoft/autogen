import sys
from typing import Any, Dict
import pytest
from autogen.agentchat.agent import Agent
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.code_utils import WIN32, in_docker_container, is_docker_running
from autogen.coding.base import CodeBlock
from autogen.coding.commandline_code_executor import CommandlineCodeExecutor
from autogen.oai.openai_utils import config_list_from_json
from conftest import skip_openai  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip_openai_tests = True
else:
    skip_openai_tests = False or skip_openai


@pytest.mark.skipif(
    sys.platform in ["win32"] or (not is_docker_running()) or (in_docker_container()),
    reason="docker is not running",
)
def test_execute_code_docker() -> None:
    _test_execute_code({"use_docker": True})


@pytest.mark.skipif(sys.platform in ["win32"], reason="do not run on windows")
def test_execute_code_local() -> None:
    _test_execute_code({"use_docker": False})


def _test_execute_code(config: Dict[str, Any]) -> None:
    executor = CommandlineCodeExecutor(**config)

    # Test single code block.
    code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output
    # Check if the docker image is set.
    if config["use_docker"] is not False:
        assert isinstance(executor.docker_image_name, str) and len(executor.docker_image_name) > 0

    # Test multiple code blocks.
    code_blocks = [
        CodeBlock(code="import sys; print('hello world!')", language="python"),
        CodeBlock(code="a = 100 + 100; print(a)", language="python"),
    ]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and "200" in code_result.output

    # Test bash script.
    code_blocks = [CodeBlock(code="echo 'hello world!'", language="bash")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output

    # Test running code and saving code to a file.
    file_lines = ["# filename: test_file_name.py", "import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
    code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and "200" in code_result.output

    # Test checking and reading saved file.
    code_blocks = [
        CodeBlock(code="import os; print(os.path.exists('test_file_name.py'))", language="python"),
        CodeBlock(code="with open('test_file_name.py') as f: print(f.readlines())", language="python"),
    ]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "True" in code_result.output
    for line in file_lines:
        assert line in code_result.output

    # Test timeout.
    executor = CommandlineCodeExecutor(**config, timeout=1)
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code and "Timeout" in code_result.output or WIN32


def test_restart() -> None:
    executor = CommandlineCodeExecutor(use_docker=True)
    # Check warning.
    with pytest.warns(UserWarning, match="Restarting command line code executor is not supported. No action is taken."):
        executor.restart()


@pytest.mark.skipif(skip_openai_tests, reason="openai not installed OR requested to skip")
def test_conversable_agent_capability() -> None:
    KEY_LOC = "notebook"
    OAI_CONFIG_LIST = "OAI_CONFIG_LIST"
    config_list = config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": {
                "gpt-3.5-turbo",
                "gpt-35-turbo",
            },
        },
    )
    llm_config = {"config_list": config_list}
    agent = ConversableAgent(
        "coding_agent",
        llm_config=llm_config,
    )
    executor = CommandlineCodeExecutor(use_docker=False)
    executor.user_capability.add_to_agent(agent)

    # Test updated system prompt.
    assert executor.user_capability.DEFAULT_SYSTEM_MESSAGE_UPDATE in agent.system_message

    # Test code generation.
    reply = agent.generate_reply(
        [{"role": "user", "content": "write a python script to print 'hello world' to the console"}],
        sender=ConversableAgent(name="user", llm_config=False),
    )

    # Test code extraction.
    code_blocks = executor.code_extractor.extract_code_blocks(reply)  # type: ignore[arg-type]
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"

    # Test code execution.
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world" in code_result.output.lower().replace(",", "")


@pytest.mark.skipif(sys.platform in ["win32"], reason="do not run on windows")
def test_conversable_agent_code_execution_no_docker() -> None:
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        _test_conversable_agent_code_execution({"use_docker": False})


@pytest.mark.skipif(
    sys.platform in ["win32"] or (not is_docker_running()) or (in_docker_container()),
    reason="docker is not running",
)
def test_conversable_agent_code_execution_docker() -> None:
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("OPENAI_API_KEY", "mock")
        _test_conversable_agent_code_execution({"use_docker": True})


def _test_conversable_agent_code_execution(config: Dict[str, Any]) -> None:
    agent = ConversableAgent(
        "user_proxy",
        code_execution_config={
            "executor": "commandline",
            "commandline": config,
        },
        llm_config=False,
    )

    isinstance(agent._code_executor, CommandlineCodeExecutor)
    code_executor: CommandlineCodeExecutor = agent._code_executor  # type: ignore[assignment]

    message = """
    Example:
    ```python
    print("hello extract code")
    ```
    """

    reply = agent.generate_reply(
        [{"role": "user", "content": message}],
        sender=ConversableAgent("user"),
    )
    assert "hello extract code" in reply  # type: ignore[operator]
    if config["use_docker"] is not False:
        # Check if the docker image is set.
        assert isinstance(code_executor.docker_image_name, str) and len(code_executor.docker_image_name) > 0


def test_conversable_agent_warning_legacy_code_executor() -> None:
    # Test warning message.
    with pytest.warns(DeprecationWarning, match="legacy code executor"):
        ConversableAgent("user_proxy", llm_config=False, code_execution_config=True)  # type: ignore[arg-type]
