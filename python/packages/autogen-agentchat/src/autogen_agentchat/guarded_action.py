"""Guarded action framework for approval-based execution."""

import asyncio
from typing import Any, Dict, List, Literal, Optional, Protocol
from autogen_core.models import LLMMessage
from .messages import BaseChatMessage, TextMessage, MultiModalMessage
from .input_func import InputFuncType


class ApprovalDeniedError(Exception):
    """Raised when a user denies approval for an action."""
    pass


MaybeRequiresApproval = Literal["always", "maybe", "never"]


class BaseApprovalGuard(Protocol):
    """Protocol for approval guards that can approve or deny actions."""
    
    async def requires_approval(
        self,
        baseline: MaybeRequiresApproval,
        llm_guess: MaybeRequiresApproval,
        action_context: List[LLMMessage],
    ) -> bool:
        """Check if the action requires approval."""
        ...

    async def get_approval(
        self, action_description: TextMessage | MultiModalMessage
    ) -> bool:
        """Get approval for the action."""
        ...


class TrivialGuardedAction:
    """A simple guarded action that checks for approval before execution."""
    
    def __init__(
        self, 
        action_name: str, 
        baseline_override: Optional[MaybeRequiresApproval] = None
    ):
        self.action_name = action_name
        self.baseline_override = baseline_override or "maybe"
    
    async def invoke_with_approval(
        self,
        action_args: Dict[str, Any],
        action_message: BaseChatMessage,
        action_context: List[LLMMessage],
        approval_guard: Optional[BaseApprovalGuard],
        action_description_for_user: TextMessage | MultiModalMessage,
    ) -> None:
        """Invoke action with approval check."""
        if approval_guard is None:
            return  # No approval guard, proceed
        
        # Check if approval is required
        requires_approval = await approval_guard.requires_approval(
            baseline=self.baseline_override,
            llm_guess="maybe",  # Conservative default
            action_context=action_context,
        )
        
        if requires_approval:
            # Get user approval
            approved = await approval_guard.get_approval(action_description_for_user)
            if not approved:
                raise ApprovalDeniedError(f"User denied approval for {self.action_name}")