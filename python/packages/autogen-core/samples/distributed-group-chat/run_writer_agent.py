import asyncio
import logging
import warnings

from _agents import BaseGroupChatAgent
from _types import AppConfig, GroupChatMessage, MessageChunk, RequestToSpeak
from _utils import get_serializers, load_config, set_all_log_levels
from autogen_core import (
    TypeSubscription,
)
from autogen_ext.models import AzureOpenAIChatCompletionClient
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime
from rich.console import Console
from rich.markdown import Markdown


async def main(config: AppConfig) -> None:
    set_all_log_levels(logging.ERROR)
    writer_agent_runtime = GrpcWorkerAgentRuntime(host_address=config.host.address)
    writer_agent_runtime.add_message_serializer(get_serializers([RequestToSpeak, GroupChatMessage, MessageChunk]))  # type: ignore[arg-type]
    await asyncio.sleep(3)
    Console().print(Markdown("Starting **`Writer Agent`**"))

    writer_agent_runtime.start()
    writer_agent_type = await BaseGroupChatAgent.register(
        writer_agent_runtime,
        config.writer_agent.topic_type,
        lambda: BaseGroupChatAgent(
            description=config.writer_agent.description,
            group_chat_topic_type=config.group_chat_manager.topic_type,
            system_message=config.writer_agent.system_message,
            model_client=AzureOpenAIChatCompletionClient(**config.client_config),
            ui_config=config.ui_agent,
        ),
    )
    await writer_agent_runtime.add_subscription(
        TypeSubscription(topic_type=config.writer_agent.topic_type, agent_type=writer_agent_type.type)
    )
    await writer_agent_runtime.add_subscription(
        TypeSubscription(topic_type=config.group_chat_manager.topic_type, agent_type=config.writer_agent.topic_type)
    )

    await writer_agent_runtime.stop_when_signal()


if __name__ == "__main__":
    set_all_log_levels(logging.ERROR)
    warnings.filterwarnings("ignore", category=UserWarning, message="Resolved model mismatch.*")
    asyncio.run(main(load_config()))
