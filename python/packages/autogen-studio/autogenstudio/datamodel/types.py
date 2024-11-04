
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from autogen_agentchat.base._task import TaskResult
from sqlmodel import (
    SQLModel,
)

# added for python3.11 and sqlmodel 0.0.22 incompatibility
if hasattr(SQLModel, "model_config"):
    SQLModel.model_config["protected_namespaces"] = ()
elif hasattr(SQLModel, "Config"):
    class CustomSQLModel(SQLModel):
        class Config:
            protected_namespaces = ()

    SQLModel = CustomSQLModel
else:
    print("Warning: Unable to set protected_namespaces.")

# pylint: disable=protected-acces


class ModelTypes(str, Enum):
    openai = "OpenAIChatCompletionClient"


class AgentTypes(str, Enum):
    assistant = "AssistantAgent"
    coding = "CodingAssistantAgent"


class TeamTypes(str, Enum):
    round_robin = "RoundRobinGroupChat"
    selector = "SelectorGroupChat"


class TerminationTypes(str, Enum):
    max_messages = "MaxMessageTermination"
    stop_message = "StopMessageTermination"
    text_mention = "TextMentionTermination"


class MessageConfig(SQLModel, table=False):
    source: str
    content: str
    message_type: str


class ModelConfig(SQLModel, table=False):
    model: str
    model_type: ModelTypes
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class ToolConfig(SQLModel, table=False):
    name: str
    description: str
    content: str


class AgentConfig(SQLModel, table=False):
    name: str
    agent_type: AgentTypes
    system_message: Optional[str] = None
    model_client: Optional[ModelConfig] = None
    tools: Optional[List[ToolConfig]] = None
    description: Optional[str] = None


class TerminationConfig(SQLModel, table=False):
    termination_type:  TerminationTypes
    max_messages: Optional[int] = None
    text: Optional[str] = None


class TeamConfig(SQLModel, table=False):
    name: str
    participants: List[AgentConfig]
    team_type: TeamTypes
    model_client: Optional[ModelConfig] = None
    termination_condition: Optional[TerminationConfig] = None


class TeamResult(SQLModel, table=False):
    task_result: TaskResult
    usage: str
    duration: float


class MessageMeta(SQLModel, table=False):
    task: Optional[str] = None
    task_result: Optional[TaskResult] = None
    summary_method: Optional[str] = "last"
    files: Optional[List[dict]] = None
    time: Optional[datetime] = None
    log: Optional[List[dict]] = None
    usage: Optional[List[dict]] = None

# web request/response data models


class Response(SQLModel, table=False):
    message: str
    status: bool
    data: Optional[Any] = None


class SocketMessage(SQLModel, table=False):
    connection_id: str
    data: Dict[str, Any]
    type: str
