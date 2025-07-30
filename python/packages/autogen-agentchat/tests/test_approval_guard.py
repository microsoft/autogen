"""Test for ApprovalGuard functionality."""

import pytest
from unittest.mock import AsyncMock
from autogen_agentchat.approval_guard import ApprovalGuard, ApprovalConfig, ApprovalResponse
from autogen_agentchat.messages import TextMessage
from autogen_core.models import SystemMessage, UserMessage, CreateResult, RequestUsage, ModelFamily
from autogen_ext.models.replay import ReplayChatCompletionClient


@pytest.mark.asyncio
async def test_approval_guard_always_policy():
    """Test approval guard with always policy."""
    approval_guard = ApprovalGuard(
        config=ApprovalConfig(approval_policy="always")
    )
    
    requires_approval = await approval_guard.requires_approval(
        baseline="never",
        llm_guess="never",
        action_context=[]
    )
    
    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_never_policy():
    """Test approval guard with never policy."""
    approval_guard = ApprovalGuard(
        config=ApprovalConfig(approval_policy="never")
    )
    
    requires_approval = await approval_guard.requires_approval(
        baseline="always",
        llm_guess="always", 
        action_context=[]
    )
    
    assert requires_approval is False


@pytest.mark.asyncio
async def test_approval_guard_user_input():
    """Test approval guard with user input function."""
    async def mock_input_func(prompt: str, cancellation_token=None):
        return "yes"
    
    approval_guard = ApprovalGuard(input_func=mock_input_func)
    
    action_description = TextMessage(
        content="Execute test code",
        source="test"
    )
    
    approved = await approval_guard.get_approval(action_description)
    assert approved is True


@pytest.mark.asyncio
async def test_approval_guard_user_input_deny():
    """Test approval guard with user denying."""
    async def mock_input_func(prompt: str, cancellation_token=None):
        return "no"
    
    approval_guard = ApprovalGuard(input_func=mock_input_func)
    
    action_description = TextMessage(
        content="Execute test code",
        source="test"
    )
    
    approved = await approval_guard.get_approval(action_description)
    assert approved is False


@pytest.mark.asyncio
async def test_approval_guard_default_approval():
    """Test approval guard with default approval when no input function."""
    approval_guard = ApprovalGuard(default_approval=False)
    
    action_description = TextMessage(
        content="Execute test code",
        source="test"
    )
    
    approved = await approval_guard.get_approval(action_description)
    assert approved is False


@pytest.mark.asyncio
async def test_approval_guard_structured_output_approval():
    """Test approval guard with structured output approval."""
    # Mock model client with structured output support
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content=ApprovalResponse(requires_approval=True, reason="Code execution requires approval"),
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": True
        }
    )
    
    approval_guard = ApprovalGuard(
        model_client=mock_client,
        config=ApprovalConfig(approval_policy="auto-conservative")
    )
    
    action_context = [
        UserMessage(content="Run python code that deletes files", source="user")
    ]
    
    requires_approval = await approval_guard.requires_approval(
        baseline="auto",
        llm_guess="auto",
        action_context=action_context
    )
    
    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_structured_output_no_approval():
    """Test approval guard with structured output no approval."""
    # Mock model client with structured output support
    mock_client = ReplayChatCompletionClient(
        [
            CreateResult(
                finish_reason="stop",
                content=ApprovalResponse(requires_approval=False, reason="Safe calculation code"),
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            )
        ],
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": True
        }
    )
    
    approval_guard = ApprovalGuard(
        model_client=mock_client,
        config=ApprovalConfig(approval_policy="auto-conservative")
    )
    
    action_context = [
        UserMessage(content="Calculate 2 + 2", source="user")
    ]
    
    requires_approval = await approval_guard.requires_approval(
        baseline="auto",
        llm_guess="auto",
        action_context=action_context
    )
    
    assert requires_approval is False


@pytest.mark.asyncio
async def test_approval_guard_json_mode_approval():
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
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": True,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False
        }
    )
    
    approval_guard = ApprovalGuard(
        model_client=mock_client,
        config=ApprovalConfig(approval_policy="auto-conservative")
    )
    
    action_context = [
        UserMessage(content="Make HTTP request to external API", source="user")
    ]
    
    requires_approval = await approval_guard.requires_approval(
        baseline="auto",
        llm_guess="auto",
        action_context=action_context
    )
    
    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_json_mode_no_approval():
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
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": True,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False
        }
    )
    
    approval_guard = ApprovalGuard(
        model_client=mock_client,
        config=ApprovalConfig(approval_policy="auto-conservative")
    )
    
    action_context = [
        UserMessage(content="Process CSV data", source="user")
    ]
    
    requires_approval = await approval_guard.requires_approval(
        baseline="auto",
        llm_guess="auto",
        action_context=action_context
    )
    
    assert requires_approval is False


@pytest.mark.asyncio
async def test_approval_guard_text_fallback_approval():
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
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False
        }
    )
    
    approval_guard = ApprovalGuard(
        model_client=mock_client,
        config=ApprovalConfig(approval_policy="auto-conservative")
    )
    
    action_context = [
        UserMessage(content="Install system packages", source="user")
    ]
    
    requires_approval = await approval_guard.requires_approval(
        baseline="auto",
        llm_guess="auto",
        action_context=action_context
    )
    
    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_text_fallback_no_approval():
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
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False
        }
    )
    
    approval_guard = ApprovalGuard(
        model_client=mock_client,
        config=ApprovalConfig(approval_policy="auto-conservative")
    )
    
    action_context = [
        UserMessage(content="Simple math calculation", source="user")
    ]
    
    requires_approval = await approval_guard.requires_approval(
        baseline="auto",
        llm_guess="auto",
        action_context=action_context
    )
    
    assert requires_approval is False


@pytest.mark.asyncio
async def test_approval_guard_json_extraction_with_backticks():
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
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": True,
            "family": ModelFamily.UNKNOWN,
            "structured_output": False
        }
    )
    
    approval_guard = ApprovalGuard(
        model_client=mock_client,
        config=ApprovalConfig(approval_policy="auto-conservative")
    )
    
    action_context = [
        UserMessage(content="Write file to disk", source="user")
    ]
    
    requires_approval = await approval_guard.requires_approval(
        baseline="auto",
        llm_guess="auto",
        action_context=action_context
    )
    
    assert requires_approval is True


@pytest.mark.asyncio
async def test_approval_guard_error_handling_fallback():
    """Test approval guard error handling with fallback to default."""
    # Mock model client that raises an exception
    mock_client = ReplayChatCompletionClient(
        [],  # Empty responses to trigger error
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "family": ModelFamily.UNKNOWN,
            "structured_output": True
        }
    )
    
    approval_guard = ApprovalGuard(
        model_client=mock_client,
        config=ApprovalConfig(approval_policy="auto-conservative"),
        default_approval=True
    )
    
    action_context = [
        UserMessage(content="Test action", source="user")
    ]
    
    requires_approval = await approval_guard.requires_approval(
        baseline="auto",
        llm_guess="auto",
        action_context=action_context
    )
    
    # Should fallback to default_approval=True when errors occur
    assert requires_approval is True