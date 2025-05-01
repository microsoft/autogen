from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Sequence

from autogen_core import ComponentBase
from pydantic import BaseModel

from autogen_agentchat.state._states import MessageStoreState

from ..messages import BaseAgentEvent, BaseChatMessage, MessageFactory


class MessageStore(ABC, ComponentBase[BaseModel]):
    """
    Abstract base class for a message store component.

    This class defines the interface for storing and managing messages in a
    message store. It provides abstract methods that must be implemented by
    subclasses, as well as concrete methods for saving and loading the state
    of the message store.
    """

    component_type = "message_store"

    def __init__(self, message_factory: MessageFactory) -> None:
        super().__init__()
        self._message_factory = message_factory

    @abstractmethod
    async def add_message(self, message: BaseAgentEvent | BaseChatMessage) -> None: ...

    """
    Add a message to the message store.

    Args:
        message (BaseAgentEvent | BaseChatMessage): The message to be added to the store.
            This can be either a BaseAgentEvent or a BaseChatMessage.
    """

    @abstractmethod
    async def add_messages(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> None: ...

    """
    Add multiple messages to the message store.

    Args:
        messages (List[BaseAgentEvent | BaseChatMessage]): A list of agent events or chat messages to add to the store.
    """

    @abstractmethod
    async def get_messages(self) -> Sequence[BaseAgentEvent | BaseChatMessage]: ...

    """
    Retrieves all messages from the message store.

    Returns:
        List[BaseAgentEvent | BaseChatMessage]: A list of all messages and events stored in the message store.
    """

    @abstractmethod
    async def reset_messages(self, messages: Optional[Sequence[BaseAgentEvent | BaseChatMessage]] = None) -> None: ...

    """
    Reset stored messages.

    This method replaces all stored messages with the provided list, or clears all messages if None is provided.

    Args:
        messages (Optional[List[BaseAgentEvent | BaseChatMessage]]): The messages to replace the current messages with.
                                                                     If None, all messages will be cleared.
    """

    async def save_state(self) -> Mapping[str, Any]:
        state = MessageStoreState(
            messages=[msg.dump() for msg in await self.get_messages()],
        )
        return state.model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        store_state = MessageStoreState.model_validate(state)
        await self.reset_messages(
            [self._message_factory.create(msg) for msg in store_state.messages],
        )
