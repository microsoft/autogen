import asyncio
import logging
import warnings

from _agents import GroupChatManager, publish_message_to_ui, publish_message_to_ui_and_backend
from _types import AppConfig, GroupChatMessage, MessageChunk, RequestToSpeak
from _utils import get_serializers, load_config, set_all_log_levels
from autogen_core import (
    TypeSubscription,
)
from autogen_core.application import WorkerAgentRuntime
from autogen_ext.models import AzureOpenAIChatCompletionClient
from rich.console import Console
from rich.markdown import Markdown

set_all_log_levels(logging.ERROR)


async def main(config: AppConfig):
    set_all_log_levels(logging.ERROR)
    group_chat_manager_runtime = WorkerAgentRuntime(host_address=config.host.address)

    group_chat_manager_runtime.add_message_serializer(get_serializers([RequestToSpeak, GroupChatMessage, MessageChunk]))  # type: ignore[arg-type]
    await asyncio.sleep(1)
    Console().print(Markdown("Starting **`Group Chat Manager`**"))
    group_chat_manager_runtime.start()
    set_all_log_levels(logging.ERROR)

    group_chat_manager_type = await GroupChatManager.register(
        group_chat_manager_runtime,
        "group_chat_manager",
        lambda: GroupChatManager(
            model_client=AzureOpenAIChatCompletionClient(**config.client_config),
            participant_topic_types=[config.writer_agent.topic_type, config.editor_agent.topic_type],
            participant_descriptions=[config.writer_agent.description, config.editor_agent.description],
            max_rounds=config.group_chat_manager.max_rounds,
            ui_config=config.ui_agent,
        ),
    )

    await group_chat_manager_runtime.add_subscription(
        TypeSubscription(topic_type=config.group_chat_manager.topic_type, agent_type=group_chat_manager_type.type)
    )

    await asyncio.sleep(5)

    await publish_message_to_ui(
        runtime=group_chat_manager_runtime,
        source="System",
        user_message="[ **Due to responsible AI considerations of this sample, group chat manager is sending an initiator message on behalf of user** ]",
        ui_config=config.ui_agent,
    )
    await asyncio.sleep(3)

    user_message: str = "Please write a short story about the gingerbread in halloween!"
    Console().print(f"Simulating User input in group chat topic:\n\t'{user_message}'")

    await publish_message_to_ui_and_backend(
        runtime=group_chat_manager_runtime,
        source="User",
        user_message=user_message,
        ui_config=config.ui_agent,
        group_chat_topic_type=config.group_chat_manager.topic_type,
    )

    await group_chat_manager_runtime.stop_when_signal()
    Console().print("Manager left the chat!")


if __name__ == "__main__":
    set_all_log_levels(logging.ERROR)
    warnings.filterwarnings("ignore", category=UserWarning, message="Resolved model mismatch.*")
    asyncio.run(main(load_config()))
