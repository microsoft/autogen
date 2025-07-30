"""Test for ApprovalGuard functionality."""

import pytest
from unittest.mock import AsyncMock
from autogen_agentchat.approval_guard import ApprovalGuard, ApprovalConfig
from autogen_agentchat.messages import TextMessage
from autogen_core.models import SystemMessage, UserMessage


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