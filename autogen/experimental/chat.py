from typing import AsyncGenerator, List, Optional, Protocol, Union, runtime_checkable

from .agent import Agent
from .types import ChatResult, IntermediateResponse, MessageAndSender, MessageContext


@runtime_checkable
class ChatOrchestrator(Protocol):
    async def step(self) -> MessageAndSender: ...

    @property
    def done(self) -> bool: ...

    @property
    def result(self) -> ChatResult: ...

    def append_message(self, message: MessageAndSender) -> None: ...

    @property
    def chat_history(self) -> List[MessageAndSender]: ...

    @property
    def message_contexts(self) -> List[Optional[MessageContext]]: ...

    @property
    def next_speaker(self) -> Agent: ...

    def reset(self) -> None: ...


@runtime_checkable
class ChatOrchestratorStream(ChatOrchestrator, Protocol):
    def stream_step(self) -> AsyncGenerator[Union[IntermediateResponse, MessageAndSender], None]: ...


# Example of driving:
# async def run(conversation: ChatOrchestrator) -> str:
#     while not conversation.done:
#         step = await conversation.step()
#         print(step)
#     return conversation.result
