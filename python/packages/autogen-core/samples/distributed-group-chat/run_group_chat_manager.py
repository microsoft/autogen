import asyncio
import warnings

from _agents import GroupChatManager
from _types import AppConfig, GroupChatMessage, RequestToSpeak
from _utils import get_serializers, load_config
from autogen_core.application import WorkerAgentRuntime
from autogen_core.components import (
    TypeSubscription,
)
from autogen_core.components._default_topic import DefaultTopicId
from autogen_core.components.models import (
    UserMessage,
)
from autogen_ext.models import AzureOpenAIChatCompletionClient
from rich.console import Console
from rich.markdown import Markdown


async def main(config: AppConfig):
    # Add group chat manager runtime
    group_chat_manager_runtime = WorkerAgentRuntime(host_address=config.host.address)

    group_chat_manager_runtime.add_message_serializer(get_serializers([RequestToSpeak, GroupChatMessage]))  # type: ignore[arg-type]
    await asyncio.sleep(1)
    Console().print(Markdown("Starting **`Group Chat Manager`**"))
    group_chat_manager_runtime.start()

    group_chat_manager_type = await GroupChatManager.register(
        group_chat_manager_runtime,
        "group_chat_manager",
        lambda: GroupChatManager(
            model_client=AzureOpenAIChatCompletionClient(**config.client_config),
            participant_topic_types=[config.writer_agent.topic_type, config.editor_agent.topic_type],
            participant_descriptions=[config.writer_agent.description, config.editor_agent.description],
            max_rounds=config.group_chat_manager.max_rounds,
        ),
    )

    await group_chat_manager_runtime.add_subscription(
        TypeSubscription(topic_type=config.group_chat_manager.topic_type, agent_type=group_chat_manager_type.type)
    )

    # This is a simple way to make sure first message gets send after all of the agents have joined
    await asyncio.sleep(5)
    user_message: str = "Please write a one line story about the gingerbread in halloween!"
    Console().print(f"Simulating User input in group chat topic:\n\t'{user_message}'")
    await group_chat_manager_runtime.publish_message(
        GroupChatMessage(
            body=UserMessage(
                content=user_message,
                source="User",
            )
        ),
        DefaultTopicId(type=config.group_chat_manager.topic_type),
    )

    await group_chat_manager_runtime.stop_when_signal()
    Console().print("Manager left the chat!")


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=UserWarning, message="Resolved model mismatch.*")
    asyncio.run(main(load_config()))
