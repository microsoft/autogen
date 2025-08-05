import asyncio
from typing import List

import pytest
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.agents._code_executor_agent import ApprovalFuncType, ApprovalRequest, ApprovalResponse
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    CodeExecutionEvent,
    CodeGenerationEvent,
    TextMessage,
)
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.replay import ReplayChatCompletionClient


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
async def test_code_generation_and_execution_with_model_client() -> None:
    """
    Tests the code generation, execution and reflection pipeline using a model client.
    """

    language = "python"
    code = 'import math\n\nnumber = 42\nsquare_root = math.sqrt(number)\nprint("%0.3f" % (square_root,))'

    model_client = ReplayChatCompletionClient(
        [f"Here is the code to calculate the square root of 42:\n```{language}\n{code}```".strip(), "TERMINATE"]
    )

    agent = CodeExecutorAgent(
        name="code_executor_agent", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

    messages = [
        TextMessage(
            content="Generate python code to calculate the square root of 42",
            source="assistant",
        )
    ]

    code_generation_event: CodeGenerationEvent | None = None
    code_execution_event: CodeExecutionEvent | None = None
    response: Response | None = None

    async for message in agent.on_messages_stream(messages, CancellationToken()):
        if isinstance(message, CodeGenerationEvent):
            code_block = message.code_blocks[0]
            assert code_block.code == code, "Code block does not match"
            assert code_block.language == language, "Language does not match"
            code_generation_event = message
        elif isinstance(message, CodeExecutionEvent):
            assert message.to_text().strip() == "6.481", f"Expected '6.481', got: {message.to_text().strip()}"
            code_execution_event = message
        elif isinstance(message, Response):
            assert isinstance(
                message.chat_message, TextMessage
            ), f"Expected TextMessage, got: {type(message.chat_message)}"
            assert (
                message.chat_message.source == "code_executor_agent"
            ), f"Expected source 'code_executor_agent', got: {message.chat_message.source}"
            response = message
        else:
            raise AssertionError(f"Unexpected message type: {type(message)}")

    assert code_generation_event is not None, "Code generation event was not received"
    assert code_execution_event is not None, "Code execution event was not received"
    assert response is not None, "Response was not received"


@pytest.mark.asyncio
async def test_no_code_response_with_model_client() -> None:
    """
    Tests agent behavior when the model client responds with non-code content.
    """

    model_client = ReplayChatCompletionClient(["The capital of France is Paris.", "TERMINATE"])

    agent = CodeExecutorAgent(
        name="code_executor_agent", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

    messages = [
        TextMessage(
            content="What is the capital of France?",
            source="assistant",
        )
    ]

    response: Response | None = None

    async for message in agent.on_messages_stream(messages, CancellationToken()):
        if isinstance(message, Response):
            assert isinstance(
                message.chat_message, TextMessage
            ), f"Expected TextMessage, got: {type(message.chat_message)}"
            assert (
                message.chat_message.source == "code_executor_agent"
            ), f"Expected source 'code_executor_agent', got: {message.chat_message.source}"
            assert (
                message.chat_message.content.strip() == "The capital of France is Paris."
            ), f"Expected 'The capital of France is Paris.', got: {message.chat_message.content.strip()}"
            response = message
        else:
            raise AssertionError(f"Unexpected message type: {type(message)}")

    assert response is not None, "Response was not received"


@pytest.mark.asyncio
async def test_self_debugging_loop() -> None:
    """
    Tests self debugging loop when the model client responds with incorrect code.
    """
    language = "python"
    incorrect_code_block = """
numbers = [10, 20, 30, 40, 50]
mean = sum(numbers) / len(numbers
print("The mean is:", mean)
""".strip()
    incorrect_code_result = """
    mean = sum(numbers) / len(numbers
                             ^
SyntaxError: '(' was never closed
""".strip()
    correct_code_block = """
numbers = [10, 20, 30, 40, 50]
mean = sum(numbers) / len(numbers)
print("The mean is:", mean)
""".strip()
    correct_code_result = """
The mean is: 30.0
""".strip()

    model_client = ReplayChatCompletionClient(
        [
            f"""
Here is the code to calculate the mean of 10, 20, 30, 40, 50

```{language}
{incorrect_code_block}
```
""",
            """{"retry": "true", "reason": "Retry 1: It is a test environment"}""",
            f"""
Here is the updated code to calculate the mean of 10, 20, 30, 40, 50

```{language}
{correct_code_block}
```""",
            "Final Response",
            "TERMINATE",
        ],
        model_info=ModelInfo(
            vision=False,
            function_calling=False,
            json_output=True,
            family=ModelFamily.UNKNOWN,
            structured_output=True,
        ),
    )

    agent = CodeExecutorAgent(
        name="code_executor_agent",
        code_executor=LocalCommandLineCodeExecutor(),
        model_client=model_client,
        max_retries_on_error=1,
    )

    messages = [
        TextMessage(
            content="Calculate the mean of 10, 20, 30, 40, 50.",
            source="assistant",
        )
    ]

    incorrect_code_generation_event: CodeGenerationEvent | None = None
    correct_code_generation_event: CodeGenerationEvent | None = None
    retry_decision_event: CodeGenerationEvent | None = None
    incorrect_code_execution_event: CodeExecutionEvent | None = None
    correct_code_execution_event: CodeExecutionEvent | None = None
    response: Response | None = None

    message_id: int = 0
    async for message in agent.on_messages_stream(messages, CancellationToken()):
        if isinstance(message, CodeGenerationEvent) and message_id == 0:
            # Step 1: First code generation
            code_block = message.code_blocks[0]
            assert code_block.code.strip() == incorrect_code_block, "Incorrect code block does not match"
            assert code_block.language == language, "Language does not match"
            incorrect_code_generation_event = message

        elif isinstance(message, CodeExecutionEvent) and message_id == 1:
            # Step 2: First code execution
            assert (
                incorrect_code_result in message.to_text().strip()
            ), f"Expected {incorrect_code_result} in execution result, got: {message.to_text().strip()}"
            incorrect_code_execution_event = message

        elif isinstance(message, CodeGenerationEvent) and message_id == 2:
            # Step 3: Retry generation with proposed correction
            retry_response = "Attempt number: 1\nProposed correction: Retry 1: It is a test environment"
            assert (
                message.to_text().strip() == retry_response
            ), f"Expected {retry_response}, got: {message.to_text().strip()}"
            retry_decision_event = message

        elif isinstance(message, CodeGenerationEvent) and message_id == 3:
            # Step 4: Second retry code generation
            code_block = message.code_blocks[0]
            assert code_block.code.strip() == correct_code_block, "Correct code block does not match"
            assert code_block.language == language, "Language does not match"
            correct_code_generation_event = message

        elif isinstance(message, CodeExecutionEvent) and message_id == 4:
            # Step 5: Second retry code execution
            assert (
                message.to_text().strip() == correct_code_result
            ), f"Expected {correct_code_result} in execution result, got: {message.to_text().strip()}"
            correct_code_execution_event = message

        elif isinstance(message, Response) and message_id == 5:
            # Step 6: Final response
            assert isinstance(
                message.chat_message, TextMessage
            ), f"Expected TextMessage, got: {type(message.chat_message)}"
            assert (
                message.chat_message.source == "code_executor_agent"
            ), f"Expected source 'code_executor_agent', got: {message.chat_message.source}"
            response = message

        else:
            raise AssertionError(f"Unexpected message type: {type(message)}")

        message_id += 1

    assert incorrect_code_generation_event is not None, "Incorrect code generation event was not received"
    assert incorrect_code_execution_event is not None, "Incorrect code execution event was not received"
    assert retry_decision_event is not None, "Retry decision event was not received"
    assert correct_code_generation_event is not None, "Correct code generation event was not received"
    assert correct_code_execution_event is not None, "Correct code execution event was not received"
    assert response is not None, "Response was not received"


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


@pytest.mark.asyncio
async def test_code_execution_agent_serialization_with_model_client() -> None:
    """Test agent config serialization"""

    model_client = ReplayChatCompletionClient(["The capital of France is Paris.", "TERMINATE"])

    agent = CodeExecutorAgent(
        name="code_executor_agent", code_executor=LocalCommandLineCodeExecutor(), model_client=model_client
    )

    # Serialize and deserialize the agent
    serialized_agent = agent.dump_component()
    deserialized_agent = CodeExecutorAgent.load_component(serialized_agent)

    assert isinstance(deserialized_agent, CodeExecutorAgent)
    assert deserialized_agent.name == "code_executor_agent"
    assert deserialized_agent._model_client is not None  # type: ignore


# Approval function test helpers
def approval_function_allow_all(request: ApprovalRequest) -> ApprovalResponse:
    """Approval function that allows all code execution."""
    return ApprovalResponse(approved=True, reason="All code is approved")


def approval_function_deny_dangerous(request: ApprovalRequest) -> ApprovalResponse:
    """Approval function that denies potentially dangerous code."""
    dangerous_keywords = ["rm ", "del ", "format", "delete", "DROP TABLE"]

    for keyword in dangerous_keywords:
        if keyword in request.code:
            return ApprovalResponse(approved=False, reason=f"Code contains potentially dangerous keyword: {keyword}")

    return ApprovalResponse(approved=True, reason="Code appears safe")


def approval_function_deny_all(request: ApprovalRequest) -> ApprovalResponse:
    """Approval function that denies all code execution."""
    return ApprovalResponse(approved=False, reason="All code execution is denied")


# Async approval function test helpers
async def async_approval_function_allow_all(request: ApprovalRequest) -> ApprovalResponse:
    """Async approval function that allows all code execution."""
    await asyncio.sleep(0.01)  # Simulate async operation
    return ApprovalResponse(approved=True, reason="All code is approved (async)")


async def async_approval_function_deny_dangerous(request: ApprovalRequest) -> ApprovalResponse:
    """Async approval function that denies potentially dangerous code."""
    await asyncio.sleep(0.01)  # Simulate async operation
    dangerous_keywords = ["rm ", "del ", "format", "delete", "DROP TABLE"]

    for keyword in dangerous_keywords:
        if keyword in request.code:
            return ApprovalResponse(
                approved=False, reason=f"Code contains potentially dangerous keyword: {keyword} (async)"
            )

    return ApprovalResponse(approved=True, reason="Code appears safe (async)")


async def async_approval_function_deny_all(request: ApprovalRequest) -> ApprovalResponse:
    """Async approval function that denies all code execution."""
    await asyncio.sleep(0.01)  # Simulate async operation
    return ApprovalResponse(approved=False, reason="All code execution is denied (async)")


@pytest.mark.asyncio
async def test_approval_functionality_no_approval() -> None:
    """Test that CodeExecutorAgent works without approval function (default behavior)."""
    agent = CodeExecutorAgent("test_agent", LocalCommandLineCodeExecutor())

    code_blocks = [CodeBlock(code="print('Hello World!')", language="python")]
    result = await agent.execute_code_block(code_blocks, CancellationToken())

    # Should execute successfully
    assert result.exit_code == 0
    assert "Hello World!" in result.output


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "approval_func,code,language,expected_exit_code,expected_in_output",
    [
        (approval_function_allow_all, "print('Approved code')", "python", 0, "Approved code"),
        (approval_function_deny_dangerous, "print('Safe code')", "python", 0, "Safe code"),
        (approval_function_deny_dangerous, "rm somefile.txt", "sh", 1, "dangerous keyword"),
        (approval_function_deny_all, "print('This should be denied')", "python", 1, "All code execution is denied"),
    ],
)
async def test_approval_functionality_sync(
    approval_func: ApprovalFuncType, code: str, language: str, expected_exit_code: int, expected_in_output: str
) -> None:
    """Test sync approval functionality with various approval functions and code samples."""
    agent = CodeExecutorAgent("test_agent", LocalCommandLineCodeExecutor(), approval_func=approval_func)

    code_blocks = [CodeBlock(code=code, language=language)]
    result = await agent.execute_code_block(code_blocks, CancellationToken())

    assert result.exit_code == expected_exit_code
    assert expected_in_output in result.output


@pytest.mark.asyncio
@pytest.mark.parametrize("is_async", [False, True])
async def test_approval_functionality_context_passed(is_async: bool) -> None:
    """Test that approval functions receive the correct context."""
    received_requests: List[ApprovalRequest] = []

    if is_async:

        async def capture_context_async(request: ApprovalRequest) -> ApprovalResponse:
            await asyncio.sleep(0.01)
            received_requests.append(request)
            return ApprovalResponse(approved=True, reason="Captured for testing (async)")

        agent = CodeExecutorAgent("test_agent", LocalCommandLineCodeExecutor(), approval_func=capture_context_async)
    else:

        def capture_context_sync(request: ApprovalRequest) -> ApprovalResponse:
            received_requests.append(request)
            return ApprovalResponse(approved=True, reason="Captured for testing")

        agent = CodeExecutorAgent("test_agent", LocalCommandLineCodeExecutor(), approval_func=capture_context_sync)

    code_blocks = [CodeBlock(code="print('Test context')", language="python")]
    await agent.execute_code_block(code_blocks, CancellationToken())

    # Verify the approval function was called and received the correct data
    assert len(received_requests) == 1
    request = received_requests[0]
    assert isinstance(request, ApprovalRequest)
    assert "print('Test context')" in request.code
    assert "```python" in request.code
    assert isinstance(request.context, list)


@pytest.mark.parametrize(
    "approval_func",
    [approval_function_allow_all, async_approval_function_allow_all],
)
def test_approval_functionality_serialization_fails(approval_func: ApprovalFuncType) -> None:
    """Test that serialization fails when approval function is set."""
    agent = CodeExecutorAgent("test_agent", LocalCommandLineCodeExecutor(), approval_func=approval_func)

    # Should raise ValueError when trying to serialize
    with pytest.raises(ValueError, match="Cannot serialize CodeExecutorAgent with approval_func set"):
        agent.dump_component()


def test_approval_functionality_serialization_succeeds() -> None:
    """Test that serialization succeeds when no approval function is set."""
    agent = CodeExecutorAgent("test_agent", LocalCommandLineCodeExecutor())

    # Should serialize successfully
    config = agent.dump_component()
    assert config.config["name"] == "test_agent"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "approval_func,async_marker",
    [
        (approval_function_deny_dangerous, ""),
        (async_approval_function_deny_dangerous, "(async)"),
    ],
)
async def test_approval_functionality_with_on_messages(approval_func: ApprovalFuncType, async_marker: str) -> None:
    """Test approval functionality works with the on_messages interface."""
    agent = CodeExecutorAgent("test_agent", LocalCommandLineCodeExecutor(), approval_func=approval_func)

    # Test with safe code
    safe_message = TextMessage(content="```python\nprint('Safe message')\n```", source="user")
    response = await agent.on_messages([safe_message], CancellationToken())
    assert isinstance(response.chat_message, TextMessage)
    assert "Safe message" in response.chat_message.content

    # Test with dangerous code
    dangerous_message = TextMessage(content="```sh\nrm -rf /\n```", source="user")
    response = await agent.on_messages([dangerous_message], CancellationToken())
    assert isinstance(response.chat_message, TextMessage)
    assert "Code execution was not approved" in response.chat_message.content
    if async_marker:
        assert async_marker in response.chat_message.content


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "approval_func,code,language,expected_exit_code,expected_in_output",
    [
        (async_approval_function_allow_all, "print('Approved async code')", "python", 0, "Approved async code"),
        (async_approval_function_deny_dangerous, "print('Safe async code')", "python", 0, "Safe async code"),
        (async_approval_function_deny_dangerous, "rm somefile.txt", "sh", 1, "dangerous keyword"),
        (
            async_approval_function_deny_all,
            "print('This should be denied async')",
            "python",
            1,
            "All code execution is denied (async)",
        ),
    ],
)
async def test_approval_functionality_async(
    approval_func: ApprovalFuncType, code: str, language: str, expected_exit_code: int, expected_in_output: str
) -> None:
    """Test async approval functionality with various approval functions and code samples."""
    agent = CodeExecutorAgent("test_agent", LocalCommandLineCodeExecutor(), approval_func=approval_func)

    code_blocks = [CodeBlock(code=code, language=language)]
    result = await agent.execute_code_block(code_blocks, CancellationToken())

    assert result.exit_code == expected_exit_code
    assert expected_in_output in result.output
