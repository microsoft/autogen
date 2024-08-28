from agnext.base.exceptions import CantHandleException

from ..base import SubscriptionInstantiationContext
from ._type_subscription import TypeSubscription


class DefaultSubscription(TypeSubscription):
    def __init__(self, topic_type: str = "default", agent_type: str | None = None):
        """The default subscription is designed to be a sensible default for applications that only need global scope for agents.

        This topic by default uses the "default" topic type and attempts to detect the agent type to use based on the instantiation context.

        Example:

            .. code-block:: python

                await runtime.register("MyAgent", agent_factory, lambda: [DefaultSubscription()])

        Args:
            topic_type (str, optional): The topic type to subscribe to. Defaults to "default".
            agent_type (str, optional): The agent type to use for the subscription. Defaults to None, in which case it will attempt to detect the agent type based on the instantiation context.
        """

        if agent_type is None:
            try:
                agent_type = SubscriptionInstantiationContext.agent_type().type
            except RuntimeError as e:
                raise CantHandleException(
                    "If agent_type is not specified DefaultSubscription must be created within the subscription callback in AgentRuntime.register"
                ) from e

        super().__init__(topic_type, agent_type)
