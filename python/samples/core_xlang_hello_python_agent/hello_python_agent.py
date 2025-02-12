import asyncio
import logging
import os
import sys

# from protos.agents_events_pb2 import NewMessageReceived
from autogen_core import (
    PROTOBUF_DATA_CONTENT_TYPE,
    AgentId,
    DefaultSubscription,
    DefaultTopicId,
    TypeSubscription,
    try_get_known_serializers_for_type,
)
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime

# Add the local package directory to sys.path
thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(thisdir, "..", ".."))
from dotenv import load_dotenv  # type: ignore # noqa: E402
from protos.agent_events_pb2 import NewMessageReceived, Output  # type: ignore # noqa: E402
from user_input import UserProxy  # type: ignore # noqa: E402

agnext_logger = logging.getLogger("autogen_core")


async def main() -> None:
    load_dotenv()
    agentHost = os.getenv("AGENT_HOST") or "localhost:53072"
    # grpc python bug - can only use the hostname, not prefix - if hostname has a prefix we have to remove it:
    if agentHost.startswith("http://"):
        agentHost = agentHost[7:]
    if agentHost.startswith("https://"):
        agentHost = agentHost[8:]
    agnext_logger.info("0")
    agnext_logger.info(agentHost)
    runtime = GrpcWorkerAgentRuntime(host_address=agentHost, payload_serialization_format=PROTOBUF_DATA_CONTENT_TYPE)

    agnext_logger.info("1")
    runtime.start()
    runtime.add_message_serializer(try_get_known_serializers_for_type(NewMessageReceived))

    agnext_logger.info("2")

    await UserProxy.register(runtime, "HelloAgent", lambda: UserProxy())
    await runtime.add_subscription(DefaultSubscription(agent_type="HelloAgent"))
    await runtime.add_subscription(TypeSubscription(topic_type="agents.NewMessageReceived", agent_type="HelloAgent"))
    await runtime.add_subscription(TypeSubscription(topic_type="agents.ConversationClosed", agent_type="HelloAgent"))
    await runtime.add_subscription(TypeSubscription(topic_type="agents.Output", agent_type="HelloAgent"))
    agnext_logger.info("3")

    new_message = NewMessageReceived(message="from Python!")
    output_message = Output(message="^v^v^v---Wild Hello from Python!---^v^v^v")

    await runtime.publish_message(
        message=new_message,
        topic_id=DefaultTopicId("agents.NewMessageReceived", "HelloAgents/python"),
        sender=AgentId("HelloAgents", "python"),
    )

    await runtime.publish_message(
        message=output_message,
        topic_id=DefaultTopicId("agents.Output", "HelloAgents"),
        sender=AgentId("HelloAgents", "python"),
    )
    await runtime.stop_when_signal()
    # await runtime.stop_when_idle()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    agnext_logger.setLevel(logging.DEBUG)
    agnext_logger.log(logging.DEBUG, "Starting worker")
    asyncio.run(main())
