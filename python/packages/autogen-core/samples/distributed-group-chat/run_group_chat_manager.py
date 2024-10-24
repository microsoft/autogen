import asyncio
import uuid

from _agents import RoundRobingGroupChatManager
from _types import AppConfig, GroupChatMessage, RequestToSpeak
from _utils import get_serializers, load_config
from autogen_core.application import WorkerAgentRuntime
from autogen_core.base._topic import TopicId
from autogen_core.components import (
    TypeSubscription,
)
from autogen_core.components.models import (
    UserMessage,
)
from rich.console import Console
from rich.markdown import Markdown


async def main(config: AppConfig):
    # Add group chat manager runtime
    group_chat_manager_runtime = WorkerAgentRuntime(host_address=config.host.address)

    group_chat_manager_runtime.add_message_serializer(get_serializers([RequestToSpeak, GroupChatMessage]))  # type: ignore[arg-type]
    await asyncio.sleep(5)
    Console().print(Markdown("Starting **`Group Chat Manager`**"))
    group_chat_manager_runtime.start()

    group_chat_manager_type = await RoundRobingGroupChatManager.register(
        group_chat_manager_runtime,
        "group_chat_manager",
        lambda: RoundRobingGroupChatManager(
            participant_topic_types=[config.writer_agent.topic_type, config.editor_agent.topic_type],
            max_rounds=config.group_chat_manager.max_rounds,
        ),
    )

    await group_chat_manager_runtime.add_subscription(
        TypeSubscription(topic_type=config.group_chat_manager.topic_type, agent_type=group_chat_manager_type.type)
    )

    await asyncio.sleep(5)
    await group_chat_manager_runtime.publish_message(
        GroupChatMessage(
            body=UserMessage(
                content="Please write a short story about the gingerbread man with photo-realistic illustrations.",
                source="User",
            )
        ),
        TopicId(type=config.group_chat_manager.topic_type, source=str(uuid.uuid4())),
    )

    await group_chat_manager_runtime.stop_when_signal()
    Console().print("Manager left the group!")


if __name__ == "__main__":
    # Make sure the file is side by side of this file
    asyncio.run(main(load_config()))
