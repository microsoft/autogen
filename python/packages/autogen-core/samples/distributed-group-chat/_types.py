from dataclasses import dataclass
from typing import Dict

from autogen_core.components.models import (
    LLMMessage,
)
from autogen_ext.models import AzureOpenAIClientConfiguration
from pydantic import BaseModel


class GroupChatMessage(BaseModel):
    """Implements a sample message sent by an LLM agent"""

    body: LLMMessage


class RequestToSpeak(BaseModel):
    """Message type for agents to speak"""

    pass


@dataclass
class MessageChunk:
    message_id: str
    text: str
    author: str
    finished: bool

    def __str__(self) -> str:
        return f"{self.author}({self.message_id}): {self.text}"


# Define Host configuration model
class HostConfig(BaseModel):
    hostname: str
    port: int

    @property
    def address(self) -> str:
        return f"{self.hostname}:{self.port}"


# Define GroupChatManager configuration model
class GroupChatManagerConfig(BaseModel):
    topic_type: str
    max_rounds: int


# Define WriterAgent configuration model
class ChatAgentConfig(BaseModel):
    topic_type: str
    description: str
    system_message: str


# Define UI Agent configuration model
class UIAgentConfig(BaseModel):
    topic_type: str
    artificial_stream_delay_seconds: Dict[str, float]

    @property
    def min_delay(self) -> float:
        return self.artificial_stream_delay_seconds.get("min", 0.0)

    @property
    def max_delay(self) -> float:
        return self.artificial_stream_delay_seconds.get("max", 0.0)


# Define the overall AppConfig model
class AppConfig(BaseModel):
    host: HostConfig
    group_chat_manager: GroupChatManagerConfig
    writer_agent: ChatAgentConfig
    editor_agent: ChatAgentConfig
    ui_agent: UIAgentConfig
    client_config: AzureOpenAIClientConfiguration = None  # type: ignore[assignment] # This was required to do custom instantiation in `load_config`
