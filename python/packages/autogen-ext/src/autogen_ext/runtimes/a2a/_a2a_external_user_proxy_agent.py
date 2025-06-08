from autogen_agentchat.agents import UserProxyAgent
from autogen_core import CancellationToken


class A2aExternalUserProxyAgent(UserProxyAgent):
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