import json

import pytest
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    TextMessage,
)
from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (
    CreateResult,
    RequestUsage,
)
from autogen_core.models._model_client import ModelFamily
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.replay import ReplayChatCompletionClient


@pytest.mark.asyncio
async def test_basic_code_execution() -> None:
    """Test basic code execution"""

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass function",
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = CodeExecutorAgent(
        name="code_executor", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

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
async def test_code_execution_error() -> None:
    """Test basic code execution"""

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass function",
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = CodeExecutorAgent(
        name="code_executor", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

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

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass function",
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = CodeExecutorAgent(
        name="code_executor", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

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

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass function",
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = CodeExecutorAgent(
        name="code_executor", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

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

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass function",
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = CodeExecutorAgent(
        name="code_executor", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

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

    model_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"input": "task"}), name="_pass_function")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                thought="Calling pass function",
                cached=False,
            ),
            "pass",
            "TERMINATE",
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": ModelFamily.GPT_4O,
            "structured_output": True,
        },
    )
    agent = CodeExecutorAgent(
        name="code_executor", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

    # Serialize and deserialize the agent
    serialized_agent = agent.dump_component()
    deserialized_agent = CodeExecutorAgent.load_component(serialized_agent)

    assert isinstance(deserialized_agent, CodeExecutorAgent)
    assert deserialized_agent.name == "code_executor"
