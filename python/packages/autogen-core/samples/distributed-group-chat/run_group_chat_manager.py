import asyncio
import logging
import warnings

import chainlit as cl  # type: ignore [reportUnknownMemberType] # This dependency is installed through instructions
from _agents import GroupChatManager
from _types import AppConfig, GroupChatMessage, RequestToSpeak
from _utils import get_serializers, load_config, set_all_log_levels
from autogen_core.application import WorkerAgentRuntime
from autogen_core.components import (
    DefaultTopicId,
    TypeSubscription,
)
from autogen_core.components.models import (
    UserMessage,
)
from autogen_ext.models import AzureOpenAIChatCompletionClient
from rich.console import Console
from rich.markdown import Markdown

set_all_log_levels(logging.ERROR)


# TODO: This is the simple hack to send messages to the UI, needs to be improved once we get some help in https://github.com/Chainlit/chainlit/issues/1491
async def send_cl(msg: str, author: str) -> None:
    await cl.Message(content=msg, author=author).send()  # type: ignore [reportAttributeAccessIssue,reportUnknownMemberType]


async def main(config: AppConfig):
    set_all_log_levels(logging.ERROR)
    group_chat_manager_runtime = WorkerAgentRuntime(host_address=config.host.address)

    # Add group chat manager runtime

    group_chat_manager_runtime.add_message_serializer(get_serializers([RequestToSpeak, GroupChatMessage]))  # type: ignore[arg-type]
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
            on_message_func=send_cl,
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


@cl.on_chat_start  # type: ignore
async def start_chat():
    set_all_log_levels(logging.ERROR)
    warnings.filterwarnings("ignore", category=UserWarning, message="Resolved model mismatch.*")
    asyncio.run(main(load_config()))


# This can be used for debugging, you can run this file using python
# if __name__ == "__main__":
#     from chainlit.cli import run_chainlit

#     set_all_log_levels(logging.ERROR)
#     run_chainlit(
#         __file__,
#     )
