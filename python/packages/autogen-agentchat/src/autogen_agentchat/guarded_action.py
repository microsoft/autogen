"""Guarded actions that can require approval before execution."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from autogen_core.models import LLMMessage

from autogen_agentchat.messages import (
    MultiModalMessage,
    TextMessage,
)

from .approval_guard import (
    DEFAULT_REQUIRES_APPROVAL,
    BaseApprovalGuard,
    MaybeRequiresApproval,
)


class ApprovalDeniedError(Exception):
    """Exception raised when an action is denied by the approval guard."""

    pass


@dataclass
class BaseGuardedAction(ABC):
    """Base class for guarded actions that may require approval."""

    name: str

    @abstractmethod
    def _get_baseline(self) -> MaybeRequiresApproval:
        """Get the baseline approval requirement for this action."""
        ...

    async def invoke_with_approval(
        self,
        call_arguments: Dict[str, Any],
        action_description: Union[TextMessage, MultiModalMessage],
        action_context: List[LLMMessage],
        action_guard: Optional[BaseApprovalGuard],
        action_description_for_user: Optional[
            Union[TextMessage, MultiModalMessage]
        ] = None,
    ) -> None:
        """
        Invokes the action with approval if the action guard is provided.

        Args:
            call_arguments: The arguments to pass to the action.
            action_description: The description of the action to be approved in its raw form.
            action_context: The context of the action to be approved.
            action_guard: The action guard to use to approve the action.
            action_description_for_user: The description of the action for the user.

        Raises:
            ApprovalDeniedError: If the action is denied by the approval guard.
        """
        needs_approval: bool = False
        if action_guard is not None:
            baseline: MaybeRequiresApproval = self._get_baseline()
            llm_guess: MaybeRequiresApproval = baseline

            # Check if the action needs approval
            needs_approval = await action_guard.requires_approval(
                baseline,
                llm_guess,
                action_context,
            )

        if needs_approval:
            assert action_guard is not None

            # Get approval for the action
            if action_description_for_user is None:
                approved = await action_guard.get_approval(action_description)
            else:
                approved = await action_guard.get_approval(
                    action_description_for_user
                )

            if not approved:
                raise ApprovalDeniedError(
                    "Action was denied by the approval guard."
                )


class TrivialGuardedAction(BaseGuardedAction):
    """A simple guarded action that doesn't perform any actual work but can be used for approval checks."""

    def __init__(
        self, name: str, baseline_override: Optional[MaybeRequiresApproval] = None
    ) -> None:
        super().__init__(name)
        self._baseline_override: MaybeRequiresApproval | None = baseline_override

    def _get_baseline(self) -> MaybeRequiresApproval:
        """Get the baseline approval requirement for this action."""
        return (
            self._baseline_override
            if self._baseline_override is not None
            else DEFAULT_REQUIRES_APPROVAL
        )
