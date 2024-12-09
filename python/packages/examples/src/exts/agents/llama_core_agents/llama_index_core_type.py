from typing import List
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

from autogen_agentchat.messages import (
    AgentMessage,
   
)
from pydantic import BaseModel



class AgentResponse(BaseModel):
    source: str
    context: List[AgentMessage]

