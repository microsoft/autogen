from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from autogen_agentchat.base import TaskResult
from autogen_core import Component, ComponentModel
from pydantic import BaseModel


class MessageConfig(BaseModel):
    source: str
    content: str
    message_type: Optional[str] = "text"


class TeamResult(BaseModel):
    task_result: TaskResult
    usage: str
    duration: float


class MessageMeta(BaseModel):
    task: Optional[str] = None
    task_result: Optional[TaskResult] = None
    summary_method: Optional[str] = "last"
    files: Optional[List[dict]] = None
    time: Optional[datetime] = None
    log: Optional[List[dict]] = None
    usage: Optional[List[dict]] = None


# web request/response data models


class Response(BaseModel):
    message: str
    status: bool
    data: Optional[Any] = None


class SocketMessage(BaseModel):
    connection_id: str
    data: Dict[str, Any]
    type: str

ComponentConfigInput = Union[str, Path, dict, ComponentModel]
