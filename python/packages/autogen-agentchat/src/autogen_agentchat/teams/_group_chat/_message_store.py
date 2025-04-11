from abc import ABC, abstractmethod
from typing import List, Optional

from ...messages import BaseChatMessage


class MessageStore(ABC):
    """
    Abstract base class for storing a message thread
    """

    @abstractmethod
    async def add_message(self, message: BaseChatMessage) -> None:
        """
        Add a message to the store
        """
        pass

    @abstractmethod
    async def add_messages(self, messages: List[BaseChatMessage]) -> None:
        """
        Add multiple messages to the store
        """
        pass

    @abstractmethod
    async def get_message_thread(self) -> List[BaseChatMessage]:
        """
        Retrieve the current message thread
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """
        Clear the message thread storage
        """
        pass

    @property
    @abstractmethod
    def ttl(self) -> Optional[float]:
        """Time-To-Live for messages in seconds."""
        pass
