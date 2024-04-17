from typing import AsyncGenerator, Optional, Protocol, Union, runtime_checkable

from .chat_history import ChatHistoryReadOnly
from .chat_result import ChatResult
from .types import IntermediateResponse, Message, MessageContext


@runtime_checkable
class ChatOrchestrator(Protocol):
    async def step(self) -> Message: ...

    @property
    def done(self) -> bool: ...

    @property
    def result(self) -> ChatResult: ...

    def append_message(self, message: Message, context: Optional[MessageContext] = None) -> None: ...

    @property
    def chat_history(self) -> ChatHistoryReadOnly: ...

    def reset(self) -> None: ...


@runtime_checkable
class ChatOrchestratorStream(ChatOrchestrator, Protocol):
    def stream_step(self) -> AsyncGenerator[Union[IntermediateResponse, Message], None]: ...


# Example of driving:
# async def run(conversation: ChatOrchestrator) -> str:
#     while not conversation.done:
#         step = await conversation.step()
#         print(step)
#     return conversation.result
