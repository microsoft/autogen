from typing import AsyncGenerator, List, Optional, Protocol, TypeVar

from autogen.experimental.agent import Agent
from autogen.experimental.termination import TerminationReason, TerminationResult
from autogen.experimental.types import ChatMessage, StreamResponse


class Chat(Protocol):
    async def step(self) -> ChatMessage: ...

    def stream_step(self) -> AsyncGenerator[StreamResponse, None]: ...

    @property
    def done(self) -> bool: ...

    @property
    def termination_result(self) -> Optional[TerminationResult]: ...

    @property
    def result(self) -> str: ...

    def append_message(self, message: ChatMessage) -> None: ...

    @property
    def chat_history(self) -> List[ChatMessage]: ...

    @property
    def next_speaker(self) -> Agent: ...


async def run(conversation: Chat) -> str:
    while not conversation.done:
        step = await conversation.step()
        print(step)
    return conversation.result
