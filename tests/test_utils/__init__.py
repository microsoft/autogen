from dataclasses import dataclass

from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken


@dataclass
class MessageType:
    ...

class LoopbackAgent(TypeRoutedAgent):
    def __init__(self) -> None:
        super().__init__("A loop back agent.")
        self.num_calls = 0


    @message_handler
    async def on_new_message(self, message: MessageType, cancellation_token: CancellationToken) -> MessageType:
        self.num_calls += 1
        return message