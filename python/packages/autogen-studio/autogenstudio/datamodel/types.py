from datetime import datetime
from typing import Any, Dict, List, Optional

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import BaseChatMessage
from autogen_core import ComponentModel
from pydantic import BaseModel


class MessageConfig(BaseModel):
    source: str
    content: str
    message_type: Optional[str] = "text"


class TeamResult(BaseModel):
    task_result: TaskResult
    usage: str
    duration: float


class LLMCallEventMessage(BaseChatMessage):
    source: str = "llm_call_event"
    content: str


class MessageMeta(BaseModel):
    task: Optional[str] = None
    task_result: Optional[TaskResult] = None
    summary_method: Optional[str] = "last"
    files: Optional[List[dict]] = None
    time: Optional[datetime] = None
    log: Optional[List[dict]] = None
    usage: Optional[List[dict]] = None


class GalleryMetadata(BaseModel):
    author: str
    created_at: datetime
    updated_at: datetime
    version: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    license: Optional[str] = None
    homepage: Optional[str] = None
    category: Optional[str] = None
    last_synced: Optional[datetime] = None


class GalleryComponents(BaseModel):
    agents: List[ComponentModel]
    models: List[ComponentModel]
    tools: List[ComponentModel]
    terminations: List[ComponentModel]


class GalleryItems(BaseModel):
    teams: List[ComponentModel]
    components: GalleryComponents


class Gallery(BaseModel):
    id: str
    name: str
    url: Optional[str] = None
    metadata: GalleryMetadata
    items: GalleryItems


# web request/response data models


class Response(BaseModel):
    message: str
    status: bool
    data: Optional[Any] = None


class SocketMessage(BaseModel):
    connection_id: str
    data: Dict[str, Any]
    type: str
