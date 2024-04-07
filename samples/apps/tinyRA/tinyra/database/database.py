from dataclasses import dataclass
from typing import Protocol, List, Optional, runtime_checkable
from pathlib import Path

from ..tools import Tool


@dataclass
class User:
    """
    Represents a user in the database.
    """

    name: str
    bio: str
    preferences: str


@dataclass
class ChatMessage:
    """
    Represents a chat message in the database.
    """

    root_id: int
    role: str
    content: str
    timestamp: float
    id: Optional[int] = None

    def __str__(self) -> str:
        return f"{self.role}: {self.content}"


@dataclass
class ChatHistory:
    """
    Represents a chat history in the database.
    """

    root_id: int
    messages: List[ChatMessage]


@runtime_checkable
class DatabaseManager(Protocol):

    async def initialize(self) -> None:
        pass

    async def reset(self) -> bool:
        pass

    async def get_chat_history(self, root_id: int) -> ChatHistory:
        pass

    async def get_chat_message(self, root_id: int, id: int) -> ChatMessage:
        pass

    async def set_chat_message(self, message: ChatMessage) -> ChatMessage:
        pass

    def sync_set_chat_message(self, message: ChatMessage) -> ChatMessage:
        pass

    async def clear_chat_history(self) -> None:
        pass

    async def get_user(self) -> User:
        pass

    async def set_user(self, user: User) -> None:
        pass

    async def get_tools(self) -> List[Tool]:
        pass

    async def get_tool_with_id(self, id: int) -> Tool:
        pass

    async def set_tool(self, tool: Tool) -> None:
        pass

    async def delete_tool(self, id: int) -> None:
        pass
