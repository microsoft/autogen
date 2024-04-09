from typing import AsyncGenerator, List, Optional, Protocol, TypeVar, runtime_checkable

from autogen.experimental.agent import Agent
from autogen.experimental.termination import TerminationReason, TerminationResult
from autogen.experimental.types import ChatMessage, StreamResponse


@runtime_checkable
class ChatOrchestrator(Protocol):
    async def step(self) -> ChatMessage: ...

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


@runtime_checkable
class ChatOrchestratorStream(ChatOrchestrator, Protocol):
    def stream_step(self) -> AsyncGenerator[StreamResponse, None]: ...


async def run(conversation: ChatOrchestrator) -> str:
    while not conversation.done:
        step = await conversation.step()
        print(step)
    return conversation.result
