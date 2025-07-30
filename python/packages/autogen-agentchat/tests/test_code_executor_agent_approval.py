"""Test for CodeExecutorAgent with ApprovalGuard integration."""

import pytest
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.approval_guard import ApprovalGuard
from autogen_agentchat.guarded_action import ApprovalDeniedError
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


@pytest.mark.asyncio
async def test_code_executor_agent_with_approval_guard_approved() -> None:
    """Test CodeExecutorAgent with approval guard when approval is granted."""

    # Mock input function that always approves
    async def mock_input_func(prompt: str, cancellation_token: CancellationToken | None = None) -> str:
        return "yes"

    approval_guard = ApprovalGuard(input_func=mock_input_func, approval_policy="always")

    agent = CodeExecutorAgent(
        name="test_code_executor", code_executor=LocalCommandLineCodeExecutor(), approval_guard=approval_guard
    )

    messages = [
        TextMessage(
            content="""
```python
print("Hello, World!")
```
""".strip(),
            source="assistant",
        )
    ]

    response = await agent.on_messages(messages, CancellationToken())

    # Should succeed because approval was granted
    assert response is not None
    assert isinstance(response.chat_message, TextMessage)
    assert "Hello, World!" in response.chat_message.content


@pytest.mark.asyncio
async def test_code_executor_agent_with_approval_guard_denied() -> None:
    """Test CodeExecutorAgent with approval guard when approval is denied."""

    # Mock input function that always denies
    async def mock_input_func(prompt: str, cancellation_token: CancellationToken | None = None) -> str:
        return "no"

    approval_guard = ApprovalGuard(input_func=mock_input_func, approval_policy="always")

    agent = CodeExecutorAgent(
        name="test_code_executor", code_executor=LocalCommandLineCodeExecutor(), approval_guard=approval_guard
    )

    messages = [
        TextMessage(
            content="""
```python
print("Hello, World!")
```
""".strip(),
            source="assistant",
        )
    ]

    # Should raise ApprovalDeniedError because approval was denied
    with pytest.raises(ApprovalDeniedError):
        await agent.on_messages(messages, CancellationToken())


@pytest.mark.asyncio
async def test_code_executor_agent_without_approval_guard() -> None:
    """Test CodeExecutorAgent without approval guard (should work normally)."""

    agent = CodeExecutorAgent(name="test_code_executor", code_executor=LocalCommandLineCodeExecutor())

    messages = [
        TextMessage(
            content="""
```python
print("Hello, World!")
```
""".strip(),
            source="assistant",
        )
    ]

    response = await agent.on_messages(messages, CancellationToken())

    # Should succeed without any approval required
    assert response is not None
    assert isinstance(response.chat_message, TextMessage)
    assert "Hello, World!" in response.chat_message.content


@pytest.mark.asyncio
async def test_code_executor_agent_approval_guard_never_policy() -> None:
    """Test CodeExecutorAgent with approval guard set to never require approval."""

    approval_guard = ApprovalGuard(approval_policy="never")

    agent = CodeExecutorAgent(
        name="test_code_executor", code_executor=LocalCommandLineCodeExecutor(), approval_guard=approval_guard
    )

    messages = [
        TextMessage(
            content="""
```python
print("Hello, World!")
```
""".strip(),
            source="assistant",
        )
    ]

    response = await agent.on_messages(messages, CancellationToken())

    # Should succeed because policy is set to never require approval
    assert response is not None
    assert isinstance(response.chat_message, TextMessage)
    assert "Hello, World!" in response.chat_message.content
