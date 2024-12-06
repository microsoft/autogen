import sys

import chainlit as cl  # type: ignore [reportUnknownMemberType] # This dependency is installed through instructions
from autogen_agentchat.messages import TextMessage
from autogen_core import (
    RoutedAgent,
    TypeSubscription,
    message_handler,
)
from autogen_core._message_context import MessageContext
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime
from chainlit import Message  # type: ignore [reportAttributeAccessIssue]

grpc_host: str = "localhost:5000"


class UIAgent(RoutedAgent):
    """Handles UI-related tasks and message processing for the distributed group chat system."""

    def __init__(self) -> None:
        super().__init__("UI Agent")

    @message_handler
    async def handle_message(self, message: TextMessage, ctx: MessageContext) -> None:
        await Message(content=message.content, author=message.source).send()


@cl.on_chat_start
async def main():
    ui_agent_runtime = GrpcWorkerAgentRuntime(host_address=grpc_host)

    print("Starting **`UI Agent`**")
    ui_agent_runtime.start()

    ui_agent_type = await UIAgent.register(
        ui_agent_runtime,
        "ui_agent",
        lambda: UIAgent(),
    )

    await ui_agent_runtime.add_subscription(
        TypeSubscription(topic_type="conversation_topic", agent_type=ui_agent_type.type)
    )

    await ui_agent_runtime.stop_when_signal()


if __name__ == "__main__":
    from chainlit.cli import run_chainlit

    if len(sys.argv) == 2:
        grpc_host = sys.argv[0]
    run_chainlit(
        __file__,
    )
