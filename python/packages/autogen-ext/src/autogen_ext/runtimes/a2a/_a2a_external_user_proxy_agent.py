from typing import Optional, Self, Any, Mapping

from autogen_agentchat.agents import UserProxyAgent
from autogen_core import CancellationToken, Component
from pydantic import BaseModel


class A2aExternalUserProxyAgentConfig(BaseModel):
    is_cancelled_by_me: bool = False

class A2aExternalUserProxyAgent(UserProxyAgent, Component[A2aExternalUserProxyAgentConfig]):
    """
    A proxy class for external user operations in the A2A system.
    This class is used to interact with external user data and operations.
    """

    def __init__(self):
        super().__init__('ExternalUser', description= "A proxy user agent to get input from external user.",input_func= self.cancel_for_user_input)
        self.is_cancelled_by_me = False


    async def cancel_for_user_input(self, _prompt: str, cancellation_token: CancellationToken)-> str:
        """
        Cancel the user input operation.
        This method can be overridden to implement custom cancellation logic.
        """
        assert cancellation_token, "IllegalState Cancellation token must be provided."
        self.is_cancelled_by_me = True
        cancellation_token.cancel()
        return "User input cancelled by the a2a external agent."

    async def on_reset(self, cancellation_token: Optional[CancellationToken] = None) -> None:
        """Reset agent state."""
        self.is_cancelled_by_me = False
        await super().on_reset(cancellation_token)


    @classmethod
    def _from_config(cls, config: Any) -> Self:
        return cls()

    async def save_state(self) -> Mapping[str, Any]:
        """Export state. Default implementation for stateless agents."""
        return A2aExternalUserProxyAgentConfig(is_cancelled_by_me=self.is_cancelled_by_me).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore agent from saved state. Default implementation for stateless agents."""
        config = A2aExternalUserProxyAgentConfig.model_validate(state)
        self.is_cancelled_by_me = config.is_cancelled_by_me
