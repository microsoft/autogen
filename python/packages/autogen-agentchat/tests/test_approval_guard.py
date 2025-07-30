"""Test for ApprovalGuard functionality."""

from typing import List

import pytest
from autogen_agentchat.approval_guard import ApprovalGuard, ApprovalResponse, BaseApprovalGuard
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_core.models import (
    CreateResult,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    UserMessage,
)
from autogen_ext.models.replay import ReplayChatCompletionClient


@pytest.mark.asyncio
async def test_approval_guard_always_policy() -> None:
    """Test approval guard with always policy."""
    approval_guard = ApprovalGuard(approval_policy="always")

    requires_approval = await approval_guard.requires_approval(baseline="never", llm_guess="never", action_context=[])

    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_never_policy() -> None:
    """Test approval guard with never policy."""
    approval_guard = ApprovalGuard(approval_policy="never")

    requires_approval = await approval_guard.requires_approval(baseline="always", llm_guess="always", action_context=[])

    assert requires_approval is False


@pytest.mark.asyncio
async def test_approval_guard_user_input() -> None:
    """Test approval guard with user input function."""

    async def mock_input_func(prompt: str, cancellation_token: CancellationToken | None = None) -> str:
        return "yes"

    approval_guard = ApprovalGuard(input_func=mock_input_func)

    action_description = TextMessage(content="Execute test code", source="test")

    approved = await approval_guard.get_approval(action_description)
    assert approved is True


@pytest.mark.asyncio
async def test_approval_guard_user_input_deny() -> None:
    """Test approval guard with user denying."""

    async def mock_input_func(prompt: str, cancellation_token: CancellationToken | None = None) -> str:
        return "no"

    approval_guard = ApprovalGuard(input_func=mock_input_func)

    action_description = TextMessage(content="Execute test code", source="test")

    approved = await approval_guard.get_approval(action_description)
    assert approved is False


@pytest.mark.asyncio
async def test_approval_guard_default_approval() -> None:
    """Test approval guard with default approval when no input function."""
    approval_guard = ApprovalGuard(default_approval=False)

    action_description = TextMessage(content="Execute test code", source="test")

    approved = await approval_guard.get_approval(action_description)
    assert approved is False


@pytest.mark.asyncio
async def test_approval_guard_structured_output_approval() -> None:
    """Test approval guard with structured output approval."""
    # Mock model client with structured output support
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content=ApprovalResponse(
                    requires_approval=True, reason="Code execution requires approval"
                ).model_dump_json(),
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=False, family=ModelFamily.UNKNOWN, structured_output=True
        ),
    )

    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative")

    action_context: List[LLMMessage] = [UserMessage(content="Run python code that deletes files", source="user")]

    requires_approval = await approval_guard.requires_approval(
        baseline="maybe", llm_guess="maybe", action_context=action_context
    )

    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_structured_output_no_approval() -> None:
    """Test approval guard with structured output no approval."""
    # Mock model client with structured output support
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content=ApprovalResponse(requires_approval=False, reason="Safe calculation code").model_dump_json(),
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=False, family=ModelFamily.UNKNOWN, structured_output=True
        ),
    )

    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative")

    action_context: List[LLMMessage] = [UserMessage(content="Calculate 2 + 2", source="user")]

    requires_approval = await approval_guard.requires_approval(
        baseline="maybe", llm_guess="maybe", action_context=action_context
    )

    assert requires_approval is False


@pytest.mark.asyncio
async def test_approval_guard_json_mode_approval() -> None:
    """Test approval guard with JSON mode approval."""
    # Mock model client with JSON output support
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content='{"requires_approval": true, "reason": "Network access requires approval"}',
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=True, family=ModelFamily.UNKNOWN, structured_output=False
        ),
    )

    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative")

    action_context: List[LLMMessage] = [UserMessage(content="Make HTTP request to external API", source="user")]

    requires_approval = await approval_guard.requires_approval(
        baseline="maybe", llm_guess="maybe", action_context=action_context
    )

    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_json_mode_no_approval() -> None:
    """Test approval guard with JSON mode no approval."""
    # Mock model client with JSON output support
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content='{"requires_approval": false, "reason": "Read-only data processing"}',
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=True, family=ModelFamily.UNKNOWN, structured_output=False
        ),
    )

    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative")

    action_context: List[LLMMessage] = [UserMessage(content="Process CSV data", source="user")]

    requires_approval = await approval_guard.requires_approval(
        baseline="maybe", llm_guess="maybe", action_context=action_context
    )

    assert requires_approval is False


@pytest.mark.asyncio
async def test_approval_guard_text_fallback_approval() -> None:
    """Test approval guard with text fallback approval."""
    # Mock model client without structured/JSON support
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content="YES",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=False, family=ModelFamily.UNKNOWN, structured_output=False
        ),
    )

    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative")

    action_context: List[LLMMessage] = [UserMessage(content="Install system packages", source="user")]

    requires_approval = await approval_guard.requires_approval(
        baseline="maybe", llm_guess="maybe", action_context=action_context
    )

    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_text_fallback_no_approval() -> None:
    """Test approval guard with text fallback no approval."""
    # Mock model client without structured/JSON support
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content="NO",
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=False, family=ModelFamily.UNKNOWN, structured_output=False
        ),
    )

    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative")

    action_context: List[LLMMessage] = [UserMessage(content="Simple math calculation", source="user")]

    requires_approval = await approval_guard.requires_approval(
        baseline="maybe", llm_guess="maybe", action_context=action_context
    )

    assert requires_approval is False


@pytest.mark.asyncio
async def test_approval_guard_json_extraction_with_backticks() -> None:
    """Test approval guard with JSON extraction from backticks."""
    # Mock model client that returns JSON in code blocks
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content='```json\n{"requires_approval": true, "reason": "File system modification"}\n```',
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=True, family=ModelFamily.UNKNOWN, structured_output=False
        ),
    )

    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative")

    action_context: List[LLMMessage] = [UserMessage(content="Write file to disk", source="user")]

    requires_approval = await approval_guard.requires_approval(
        baseline="maybe", llm_guess="maybe", action_context=action_context
    )

    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_error_handling_fallback() -> None:
    """Test approval guard error handling with fallback to default."""
    # Mock model client that raises an exception
    mock_client = ReplayChatCompletionClient(
        [],  # Empty responses to trigger error
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=False, family=ModelFamily.UNKNOWN, structured_output=True
        ),
    )

    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative", default_approval=True)

    action_context: List[LLMMessage] = [UserMessage(content="Test action", source="user")]

    requires_approval = await approval_guard.requires_approval(
        baseline="maybe", llm_guess="maybe", action_context=action_context
    )

    # Should fallback to default_approval=True when errors occur
    assert requires_approval is True


def test_approval_guard_component() -> None:
    mock_client = ReplayChatCompletionClient(
        [],  # Empty responses to trigger error
        model_info=ModelInfo(
            vision=False, function_calling=False, json_output=False, family=ModelFamily.UNKNOWN, structured_output=True
        ),
    )
    approval_guard = ApprovalGuard(model_client=mock_client, approval_policy="auto-conservative", default_approval=True)

    config = approval_guard.dump_component()
    loaded = BaseApprovalGuard.load_component(config)
    assert isinstance(loaded, ApprovalGuard)
    assert loaded.approval_policy == "auto-conservative"
    assert loaded.default_approval is True
    assert isinstance(loaded.model_client, ReplayChatCompletionClient)


def test_approval_guard_dump_component_with_custom_input_func() -> None:
    async def custom_input_func(prompt: str, cancellation_token: CancellationToken | None = None) -> str:
        return "yes"

    approval_guard = ApprovalGuard(input_func=custom_input_func, approval_policy="always")

    with pytest.raises(ValueError, match="Cannot convert to config with custom input function set in ApprovalGuard."):
        approval_guard.dump_component()
