from typing import List
from autogen_core.models import LLMMessage
from pydantic import BaseModel


class UserLogin(BaseModel):
    pass

class UserTask(BaseModel):
    context: List[LLMMessage]

class AgentResponse(BaseModel):
    reply_to_topic_type: str
    context: List[LLMMessage]
