"""Guarded action framework for approval-based execution."""

from typing import Any, Dict, List, Literal, Optional

from autogen_core.models import LLMMessage

from .approval_guard import BaseApprovalGuard, MaybeRequiresApproval
from .messages import BaseChatMessage, MultiModalMessage, TextMessage


class ApprovalDeniedError(Exception):
    """Raised when a user denies approval for an action."""

    pass


class TrivialGuardedAction:
    """A simple guarded action that checks for approval before execution."""

    def __init__(self, action_name: str, baseline_override: Optional[MaybeRequiresApproval] = None):
        self.action_name = action_name
        self.baseline_override: Literal[MaybeRequiresApproval] = baseline_override or "maybe"

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


__all__ = [
    "ApprovalDeniedError",
    "TrivialGuardedAction",
]
