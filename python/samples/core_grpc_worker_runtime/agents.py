from dataclasses import dataclass

from autogen_core import DefaultTopicId, MessageContext, RoutedAgent, default_subscription, message_handler


@dataclass
class CascadingMessage:
    round: int


@dataclass
class ReceiveMessageEvent:
    round: int
    sender: str
    recipient: str


@default_subscription
class CascadingAgent(RoutedAgent):
    def __init__(self, max_rounds: int) -> None:
        super().__init__("A cascading agent.")
        self.max_rounds = max_rounds

    @message_handler
    async def on_new_message(self, message: CascadingMessage, ctx: MessageContext) -> None:
        await self.publish_message(
            ReceiveMessageEvent(round=message.round, sender=str(ctx.sender), recipient=str(self.id)),
            topic_id=DefaultTopicId(),
        )
        if message.round == self.max_rounds:
            return
        await self.publish_message(CascadingMessage(round=message.round + 1), topic_id=DefaultTopicId())


@default_subscription
class ObserverAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("An observer agent.")

    @message_handler
    async def on_receive_message(self, message: ReceiveMessageEvent, ctx: MessageContext) -> None:
        print(f"[Round {message.round}]: Message from {message.sender} to {message.recipient}.")
