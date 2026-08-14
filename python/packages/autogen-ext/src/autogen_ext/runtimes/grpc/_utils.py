from autogen_core._subscription import Subscription
from autogen_core._type_prefix_subscription import TypePrefixSubscription
from autogen_core._type_subscription import TypeSubscription

from .protos import agent_worker_pb2


def subscription_to_proto(subscription: Subscription) -> agent_worker_pb2.Subscription:
    match subscription:
        case TypeSubscription(topic_type=topic_type, agent_type=agent_type, id=id):
            return agent_worker_pb2.Subscription(
                id=id,
                typeSubscription=agent_worker_pb2.TypeSubscription(topic_type=topic_type, agent_type=agent_type),
            )
        case TypePrefixSubscription(topic_type_prefix=topic_type_prefix, agent_type=agent_type, id=id):
            return agent_worker_pb2.Subscription(
                id=id,
                typePrefixSubscription=agent_worker_pb2.TypePrefixSubscription(
                    topic_type_prefix=topic_type_prefix, agent_type=agent_type
                ),
            )
        case _:
            raise ValueError("Unsupported subscription type.")


def subscription_from_proto(subscription: agent_worker_pb2.Subscription) -> Subscription:
    oneofcase = subscription.WhichOneof("subscription")
    match oneofcase:
        case "typeSubscription":
            type_subscription_msg: agent_worker_pb2.TypeSubscription = subscription.typeSubscription
            return TypeSubscription(
                topic_type=type_subscription_msg.topic_type,
                agent_type=type_subscription_msg.agent_type,
                id=subscription.id,
            )

        case "typePrefixSubscription":
            type_prefix_subscription_msg: agent_worker_pb2.TypePrefixSubscription = subscription.typePrefixSubscription
            return TypePrefixSubscription(
                topic_type_prefix=type_prefix_subscription_msg.topic_type_prefix,
                agent_type=type_prefix_subscription_msg.agent_type,
                id=subscription.id,
            )
        case None:
            raise ValueError("Invalid subscription message.")
