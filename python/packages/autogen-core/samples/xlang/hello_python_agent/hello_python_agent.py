import asyncio
import logging
import os
import sys

thisdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(thisdir, "..", ".."))

from autogen_core.application import WorkerAgentRuntime
from protos.agent_events_pb2 import NewMessageReceived

# from protos.agents_events_pb2 import NewMessageReceived
from autogen_core.base import AgentId, try_get_known_serializers_for_type
from autogen_core.components import DefaultSubscription, DefaultTopicId

# Add the local package directory to sys.path
# sys.path.append(os.path.abspath('../../../../python/packages/autogen-core'))
from dotenv import load_dotenv
from user_input import UserProxy

agnext_logger = logging.getLogger("autogen_core")


async def main() -> None:
    load_dotenv()
    agentHost = os.getenv("AGENT_HOST") or "localhost:53072"
    # stupid grpc python bug - can only use the hostname, not prefix - if hostname has a prefix we have to remove it:
    if agentHost.startswith("http://"):
        agentHost = agentHost[7:]
    if agentHost.startswith("https://"):
        agentHost = agentHost[8:]
    agnext_logger.info("0")
    agnext_logger.info(agentHost)
    runtime = WorkerAgentRuntime(host_address=agentHost)

    agnext_logger.info("1")
    runtime.start()
    runtime.add_message_serializer(try_get_known_serializers_for_type(NewMessageReceived))

    agnext_logger.info("2")

    await UserProxy.register(runtime, "HelloAgents", lambda: UserProxy())
    await runtime.add_subscription(DefaultSubscription(agent_type="HelloAgents"))
    agnext_logger.info("3")

    message = NewMessageReceived(message="Hello from Python!")

    await runtime.publish_message(
        message=message,
        topic_id=DefaultTopicId("agents.NewMessageReceived"),
        sender=AgentId("HelloAgents", "python"),
    )
    await runtime.stop_when_signal()
    # await runtime.stop_when_idle()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    agnext_logger.setLevel(logging.DEBUG)
    agnext_logger.log(logging.DEBUG, "Starting worker")
    asyncio.run(main())
