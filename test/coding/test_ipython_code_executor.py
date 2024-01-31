import os
import tempfile
import uuid
import pytest
from autogen.agentchat.agent import Agent
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.coding.base import CodeBlock
from autogen.coding.ipython_code_executor import IPythonCodeExecutor
from autogen.oai.openai_utils import config_list_from_json
from conftest import skip_openai  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip_openai_tests = True
else:
    skip_openai_tests = False or skip_openai


def test_execute_code_single_code_block() -> None:
    executor = IPythonCodeExecutor()
    code_blocks = [CodeBlock(code="import sys\nprint('hello world!')", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output


def test_execute_code_multiple_code_blocks() -> None:
    executor = IPythonCodeExecutor()
    code_blocks = [
        CodeBlock(code="import sys\na = 123 + 123\n", language="python"),
        CodeBlock(code="print(a)", language="python"),
    ]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "246" in code_result.output

    msg = """
def test_function(a, b):
    return a + b
"""
    code_blocks = [
        CodeBlock(code=msg, language="python"),
        CodeBlock(code="test_function(431, 423)", language="python"),
    ]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "854" in code_result.output


def test_execute_code_bash_script() -> None:
    executor = IPythonCodeExecutor()
    # Test bash script.
    code_blocks = [CodeBlock(code='!echo "hello world!"', language="bash")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output


def test_saving_to_file() -> None:
    executor = IPythonCodeExecutor()
    with tempfile.TemporaryDirectory() as tmpdirname:
        code = f"""
with open('{os.path.join(tmpdirname, "test_file_name")}', 'w') as f:
    f.write('test saving file')
"""
        code_blocks = [CodeBlock(code=code, language="python")]
        code_result = executor.execute_code_blocks(code_blocks)
        assert code_result.exit_code == 0 and os.path.exists(os.path.join(tmpdirname, "test_file_name"))


def test_timeout() -> None:
    executor = IPythonCodeExecutor(timeout=1)
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code and "Timeout" in code_result.output


def test_silent_pip_install() -> None:
    executor = IPythonCodeExecutor()
    code_blocks = [CodeBlock(code="!pip install matplotlib numpy", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and code_result.output.strip() == ""

    none_existing_package = uuid.uuid4().hex
    code_blocks = [CodeBlock(code=f"!pip install matplotlib_{none_existing_package}", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "ERROR: " in code_result.output


def test_restart() -> None:
    executor = IPythonCodeExecutor()
    code_blocks = [CodeBlock(code="x = 123", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and code_result.output.strip() == ""

    executor.restart()
    code_blocks = [CodeBlock(code="print(x)", language="python")]
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code and "NameError" in code_result.output


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
    executor = IPythonCodeExecutor()
    executor.user_capability.add_to_agent(agent)

    # Test updated system prompt.
    assert executor.user_capability.DEFAULT_SYSTEM_MESSAGE_UPDATE in agent.system_message

    # Test code generation.
    reply = agent.generate_reply(
        [{"role": "user", "content": "print 'hello world' to the console"}],
        sender=ConversableAgent("user"),
    )

    # Test code extraction.
    code_blocks = executor.code_extractor.extract_code_blocks(reply)  # type: ignore[arg-type]
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"

    # Test code execution.
    code_result = executor.execute_code_blocks(code_blocks)
    assert code_result.exit_code == 0 and "hello world" in code_result.output.lower()


def test_conversable_agent_code_execution() -> None:
    agent = ConversableAgent("user_proxy", llm_config=False, code_execution_config={"executor": "ipython"})
    msg = """
Run this code:
```python
def test_function(a, b):
    return a * b
```
And then this:
```python
print(test_function(123, 4))
```
"""
    reply = agent.generate_reply([{"role": "user", "content": msg}], sender=ConversableAgent("user"))
    assert "492" in reply  # type: ignore[operator]
