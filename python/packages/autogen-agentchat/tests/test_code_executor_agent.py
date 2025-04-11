import pytest
from autogen_core import CancellationToken
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    CodeExecutionEvent,
    CodeGenerationEvent,
    TextMessage,
)


@pytest.mark.asyncio
async def test_basic_code_execution() -> None:
    """Test basic code execution"""

    agent = CodeExecutorAgent(name="code_executor", code_executor=LocalCommandLineCodeExecutor())

    messages = [
        TextMessage(
            content="""
```python
import math

number = 42
square_root = math.sqrt(number)
print("%0.3f" % (square_root,))
```
""".strip(),
            source="assistant",
        )
    ]
    response = await agent.on_messages(messages, CancellationToken())

    assert isinstance(response, Response)
    assert isinstance(response.chat_message, TextMessage)
    assert response.chat_message.content.strip() == "6.481"
    assert response.chat_message.source == "code_executor"


@pytest.mark.asyncio
async def test_basic_code_execution_with_model_client() -> None:
    """Test basic code execution"""

    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    agent = CodeExecutorAgent(
        name="code_executor_agent", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

    messages = [
        TextMessage(
            content="Generate python code to print 'Hello World!' on console.",
            source="assistant",
        )
    ]

    async for message in agent.on_messages_stream(messages, CancellationToken()):
        if isinstance(message, CodeGenerationEvent):
            pass  # Do nothing for CodeGenerationEvent
        elif isinstance(message, CodeExecutionEvent):
            assert (
                message.to_text().strip() == "Hello World!"
            ), f"Expected 'Hello World!', got: {message.to_text().strip()}"
        elif isinstance(message, Response):
            assert isinstance(
                message.chat_message, TextMessage
            ), f"Expected TextMessage, got: {type(message.chat_message)}"
            assert (
                message.chat_message.source == "code_executor_agent"
            ), f"Expected source 'code_executor_agent', got: {message.chat_message.source}"
        else:
            raise AssertionError(f"Unexpected message type: {type(message)}")


@pytest.mark.asyncio
async def test_code_execution_error() -> None:
    """Test basic code execution"""

    agent = CodeExecutorAgent(name="code_executor", code_executor=LocalCommandLineCodeExecutor())

    messages = [
        TextMessage(
            content="""
```python
import math

number = -1.0
square_root = math.sqrt(number)
print("%0.3f" % (square_root,))
```
""".strip(),
            source="assistant",
        )
    ]
    response = await agent.on_messages(messages, CancellationToken())

    assert isinstance(response, Response)
    assert isinstance(response.chat_message, TextMessage)
    assert "The script ran, then exited with an error (POSIX exit code: 1)" in response.chat_message.content
    assert "ValueError: math domain error" in response.chat_message.content


@pytest.mark.asyncio
async def test_code_execution_no_output() -> None:
    """Test basic code execution"""

    agent = CodeExecutorAgent(name="code_executor", code_executor=LocalCommandLineCodeExecutor())

    messages = [
        TextMessage(
            content="""
```python
import math

number = 42
square_root = math.sqrt(number)
```
""".strip(),
            source="assistant",
        )
    ]
    response = await agent.on_messages(messages, CancellationToken())

    assert isinstance(response, Response)
    assert isinstance(response.chat_message, TextMessage)
    assert (
        "The script ran but produced no output to console. The POSIX exit code was: 0. If you were expecting output, consider revising the script to ensure content is printed to stdout."
        in response.chat_message.content
    )


@pytest.mark.asyncio
async def test_code_execution_no_block() -> None:
    """Test basic code execution"""

    agent = CodeExecutorAgent(name="code_executor", code_executor=LocalCommandLineCodeExecutor())

    messages = [
        TextMessage(
            content="""
import math

number = 42
square_root = math.sqrt(number)
""".strip(),
            source="assistant",
        )
    ]
    response = await agent.on_messages(messages, CancellationToken())

    assert isinstance(response, Response)
    assert isinstance(response.chat_message, TextMessage)
    assert (
        "No code blocks found in the thread. Please provide at least one markdown-encoded code block"
        in response.chat_message.content
    )


@pytest.mark.asyncio
async def test_code_execution_multiple_blocks() -> None:
    """Test basic code execution"""

    agent = CodeExecutorAgent(name="code_executor", code_executor=LocalCommandLineCodeExecutor())

    messages = [
        TextMessage(
            content="""
```python
import math

number = 42
square_root = math.sqrt(number)
print("%0.3f" % (square_root,))
```

And also:

```python
import time
print(f"The current time is: {time.time()}")

```

And this should result in an error:
```python
import math

number = -1.0
square_root = math.sqrt(number)
print("%0.3f" % (square_root,))
```

""".strip(),
            source="assistant",
        )
    ]
    response = await agent.on_messages(messages, CancellationToken())

    assert isinstance(response, Response)
    assert isinstance(response.chat_message, TextMessage)
    assert "6.481" in response.chat_message.content
    assert "The current time is:" in response.chat_message.content
    assert "The script ran, then exited with an error (POSIX exit code: 1)" in response.chat_message.content
    assert "ValueError: math domain error" in response.chat_message.content


@pytest.mark.asyncio
async def test_code_execution_agent_serialization() -> None:
    """Test agent config serialization"""

    agent = CodeExecutorAgent(name="code_executor", code_executor=LocalCommandLineCodeExecutor())

    # Serialize and deserialize the agent
    serialized_agent = agent.dump_component()
    deserialized_agent = CodeExecutorAgent.load_component(serialized_agent)

    assert isinstance(deserialized_agent, CodeExecutorAgent)
    assert deserialized_agent.name == "code_executor"
