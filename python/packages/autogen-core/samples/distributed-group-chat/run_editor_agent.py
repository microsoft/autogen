import asyncio
import logging
import warnings

from _agents import BaseGroupChatAgent
from _types import AppConfig, GroupChatMessage, MessageChunk, RequestToSpeak
from _utils import get_serializers, load_config, set_all_log_levels
from autogen_core import (
    TypeSubscription,
)
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime
from rich.console import Console
from rich.markdown import Markdown


async def main(config: AppConfig):
    set_all_log_levels(logging.ERROR)
    editor_agent_runtime = GrpcWorkerAgentRuntime(host_address=config.host.address)
    editor_agent_runtime.add_message_serializer(get_serializers([RequestToSpeak, GroupChatMessage, MessageChunk]))  # type: ignore[arg-type]
    await asyncio.sleep(4)
    Console().print(Markdown("Starting **`Editor Agent`**"))
    editor_agent_runtime.start()
    editor_agent_type = await BaseGroupChatAgent.register(
        editor_agent_runtime,
        config.editor_agent.topic_type,
        lambda: BaseGroupChatAgent(
            description=config.editor_agent.description,
            group_chat_topic_type=config.group_chat_manager.topic_type,
            system_message=config.editor_agent.system_message,
            model_client=AzureOpenAIChatCompletionClient(**config.client_config),
            ui_config=config.ui_agent,
        ),
    )
    await editor_agent_runtime.add_subscription(
        TypeSubscription(topic_type=config.editor_agent.topic_type, agent_type=editor_agent_type.type)
    )
    await editor_agent_runtime.add_subscription(
        TypeSubscription(topic_type=config.group_chat_manager.topic_type, agent_type=editor_agent_type.type)
    )

    await editor_agent_runtime.stop_when_signal()


if __name__ == "__main__":
    set_all_log_levels(logging.ERROR)
    warnings.filterwarnings("ignore", category=UserWarning, message="Resolved model mismatch.*")
    asyncio.run(main(load_config()))
