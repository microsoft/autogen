import sys
import tempfile
import pytest
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.coding.base import CodeBlock, CodeExecutor
from autogen.coding.factory import CodeExecutorFactory
from autogen.coding.local_commandline_code_executor import LocalCommandlineCodeExecutor
from autogen.oai.openai_utils import config_list_from_json

from conftest import MOCK_OPEN_AI_API_KEY, skip_openai


def test_create() -> None:
    config = {"executor": "commandline-local"}
    executor = CodeExecutorFactory.create(config)
    assert isinstance(executor, LocalCommandlineCodeExecutor)

    config = {"executor": LocalCommandlineCodeExecutor()}
    executor = CodeExecutorFactory.create(config)
    assert executor is config["executor"]


def test_local_commandline_executor_init() -> None:
    executor = LocalCommandlineCodeExecutor(timeout=10, work_dir=".")
    assert executor.timeout == 10 and executor.work_dir == "."

    # Try invalid working directory.
    with pytest.raises(ValueError, match="Working directory .* does not exist."):
        executor = LocalCommandlineCodeExecutor(timeout=111, work_dir="/invalid/directory")


def test_local_commandline_executor_execute_code() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandlineCodeExecutor(work_dir=temp_dir)
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


@pytest.mark.skipif(sys.platform in ["win32"], reason="do not run on windows")
def test_local_commandline_code_executor_timeout() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandlineCodeExecutor(timeout=1, work_dir=temp_dir)
        _test_timeout(executor)


def _test_timeout(executor: CodeExecutor) -> None:
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code and "Timeout" in code_result.output


def test_local_commandline_code_executor_restart() -> None:
    executor = LocalCommandlineCodeExecutor()
    _test_restart(executor)


def _test_restart(executor: CodeExecutor) -> None:
    # Check warning.
    with pytest.warns(UserWarning, match=r".*No action is taken."):
        executor.restart()


@pytest.mark.skipif(skip_openai, reason="requested to skip openai tests")
def test_local_commandline_executor_conversable_agent_capability() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandlineCodeExecutor(work_dir=temp_dir)
        _test_conversable_agent_capability(executor=executor)


def _test_conversable_agent_capability(executor: CodeExecutor) -> None:
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
        code_execution_config=False,
    )
    executor.user_capability.add_to_agent(agent)

    # Test updated system prompt.
    assert executor.DEFAULT_SYSTEM_MESSAGE_UPDATE in agent.system_message

    # Test code generation.
    reply = agent.generate_reply(
        [{"role": "user", "content": "write a python script to print 'hello world' to the console"}],
        sender=ConversableAgent(name="user", llm_config=False, code_execution_config=False),
    )

    # Test code extraction.
    code_blocks = executor.code_extractor.extract_code_blocks(reply)  # type: ignore[arg-type]
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"

    # Test code execution.
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world" in code_result.output.lower().replace(",", "")


def test_local_commandline_executor_conversable_agent_code_execution() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandlineCodeExecutor(work_dir=temp_dir)
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
