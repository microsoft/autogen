from typing import Callable, Type, TypeVar, overload

from ..base import BaseAgent, SubscriptionInstantiationContext, subscription_factory
from ..base.exceptions import CantHandleException
from ._type_subscription import TypeSubscription


class DefaultSubscription(TypeSubscription):
    """The default subscription is designed to be a sensible default for applications that only need global scope for agents.

    This topic by default uses the "default" topic type and attempts to detect the agent type to use based on the instantiation context.

    Args:
        topic_type (str, optional): The topic type to subscribe to. Defaults to "default".
        agent_type (str, optional): The agent type to use for the subscription. Defaults to None, in which case it will attempt to detect the agent type based on the instantiation context.
    """

    def __init__(self, topic_type: str = "default", agent_type: str | None = None):
        if agent_type is None:
            try:
                agent_type = SubscriptionInstantiationContext.agent_type().type
            except RuntimeError as e:
                raise CantHandleException(
                    "If agent_type is not specified DefaultSubscription must be created within the subscription callback in AgentRuntime.register"
                ) from e

        super().__init__(topic_type, agent_type)


BaseAgentType = TypeVar("BaseAgentType", bound="BaseAgent")


@overload
def default_subscription() -> Callable[[Type[BaseAgentType]], Type[BaseAgentType]]: ...


@overload
def default_subscription(cls: Type[BaseAgentType]) -> Type[BaseAgentType]: ...


def default_subscription(
    cls: Type[BaseAgentType] | None = None,
) -> Callable[[Type[BaseAgentType]], Type[BaseAgentType]] | Type[BaseAgentType]:
    if cls is None:
        return subscription_factory(lambda: [DefaultSubscription()])
    else:
        return subscription_factory(lambda: [DefaultSubscription()])(cls)


def type_subscription(topic_type: str) -> Callable[[Type[BaseAgentType]], Type[BaseAgentType]]:
    return subscription_factory(lambda: [DefaultSubscription(topic_type=topic_type)])
