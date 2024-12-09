from agents import CascadingMessage, ObserverAgent
from autogen_core import DefaultTopicId, try_get_known_serializers_for_type
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime


async def main() -> None:
    runtime = GrpcWorkerAgentRuntime(host_address="localhost:50051")
    runtime.add_message_serializer(try_get_known_serializers_for_type(CascadingMessage))
    runtime.start()
    await ObserverAgent.register(runtime, "observer_agent", lambda: ObserverAgent())
    await runtime.publish_message(CascadingMessage(round=1), topic_id=DefaultTopicId())
    await runtime.stop_when_signal()


if __name__ == "__main__":
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    # logger = logging.getLogger("autogen_core")
    import asyncio

    asyncio.run(main())
