import asyncio
import logging
import os
import sys

from autogen_core.application import SingleThreadedAgentRuntime, WorkerAgentRuntime
from autogen_core.application.protos.agent_events_pb2 import Input
from autogen_core.base import MessageContext, try_get_known_serializers_for_type
from autogen_core.components import DefaultSubscription, DefaultTopicId, RoutedAgent, message_handler

# Add the local package directory to sys.path
# sys.path.append(os.path.abspath('../../../../python/packages/autogen-core'))
from dotenv import load_dotenv
from user_input import UserProxy

agnext_logger = logging.getLogger("autogen_core")


async def main() -> None:
    load_dotenv()
    agentHost = os.getenv("AGENT_HOST")
    agnext_logger.info("0")
    agnext_logger.info(agentHost)
    runtime = WorkerAgentRuntime(host_address=agentHost)

    agnext_logger.info("1")
    runtime.start()
    runtime.add_message_serializer(try_get_known_serializers_for_type(Input))

    agnext_logger.info("2")

    await UserProxy.register(runtime, "proxy", lambda: UserProxy())
    await runtime.add_subscription(DefaultSubscription(agent_type="proxy"))
    agnext_logger.info("3")

    await runtime.publish_message(message=Input(message=""), topic_id="HelloAgents")
    await runtime.stop_when_signal()
    # await runtime.stop_when_idle()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    agnext_logger.setLevel(logging.DEBUG)
    agnext_logger.log(logging.DEBUG, "Starting worker")
    asyncio.run(main())
