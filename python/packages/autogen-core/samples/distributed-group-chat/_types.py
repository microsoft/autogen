from autogen_core.components.models import (
    LLMMessage,
)
from autogen_core.components.models.config import AzureOpenAIClientConfiguration
from pydantic import BaseModel


class GroupChatMessage(BaseModel):
    """Implements a sample message sent by an LLM agent"""

    body: LLMMessage


class RequestToSpeak(BaseModel):
    """Message type for agents to speak"""

    pass


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


# Define the overall AppConfig model
class AppConfig(BaseModel):
    host: HostConfig
    group_chat_manager: GroupChatManagerConfig
    writer_agent: ChatAgentConfig
    editor_agent: ChatAgentConfig
    client_config: AzureOpenAIClientConfiguration = None  # type: ignore[assignment] # This was required to do custom instantiation in `load_config``
