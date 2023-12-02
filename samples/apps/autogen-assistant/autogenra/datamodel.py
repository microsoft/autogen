import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional, Union
from pydantic.dataclasses import dataclass
from dataclasses import asdict, field


@dataclass
class Message(object):
    user_id: str
    role: str
    content: str
    root_msg_id: Optional[str] = None
    msg_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    personalize: Optional[bool] = False
    ra: Optional[str] = None
    code: Optional[str] = None
    metadata: Optional[Any] = None
    session_id: Optional[str] = None

    def __post_init__(self):
        if self.msg_id is None:
            self.msg_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def dict(self):
        result = asdict(self)
        result["timestamp"] = result["timestamp"].isoformat()
        return result


# web api data models


# autogenflow data models
@dataclass
class ModelConfig:
    """Data model for Model Config item in LLMConfig for Autogen"""

    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    api_type: Optional[str] = None
    api_version: Optional[str] = None


@dataclass
class LLMConfig:
    """Data model for LLM Config for Autogen"""

    config_list: List[Any] = field(default_factory=List)
    temperature: float = 0
    cache_seed: Optional[Union[int, None]] = None
    timeout: Optional[int] = None


@dataclass
class AgentConfig:
    """Data model for Agent Config for Autogen"""

    name: str
    llm_config: Optional[Union[LLMConfig, bool]] = False
    human_input_mode: str = "NEVER"
    max_consecutive_auto_reply: int = 10
    system_message: Optional[str] = None
    is_termination_msg: Optional[Union[bool, str, Callable]] = None
    code_execution_config: Optional[Union[bool, str, Dict[str, Any]]] = None


@dataclass
class AgentFlowSpec:
    """Data model to help flow load agents from config"""

    type: Literal["assistant", "userproxy", "groupchat"]
    config: AgentConfig = field(default_factory=AgentConfig)


@dataclass
class AgentWorkFlowConfig:
    """Data model for Flow Config for Autogen"""

    name: str
    sender: AgentFlowSpec
    receiver: Union[AgentFlowSpec, List[AgentFlowSpec]]
    type: Literal["default", "groupchat"] = "default"

    def dict(self):
        return asdict(self)


@dataclass
class Session(object):
    """Data model for AutoGen Chat Session"""

    user_id: str
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    flow_config: AgentWorkFlowConfig = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())

    def dict(self):
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class Gallery(object):
    """Data model for Gallery Item"""

    session: Session
    messages: List[Message]
    tags: List[str]
    id: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.id is None:
            self.id = str(uuid.uuid4())

    def dict(self):
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


@dataclass
class ChatWebRequestModel(object):
    """Data model for Chat Web Request for Web End"""

    message: Message
    flow_config: AgentWorkFlowConfig


@dataclass
class DeleteMessageWebRequestModel(object):
    user_id: str
    msg_id: str
    session_id: Optional[str] = None


@dataclass
class CreateSkillWebRequestModel(object):
    user_id: str
    skills: Union[str, List[str]]


@dataclass
class DBWebRequestModel(object):
    user_id: str
    msg_id: Optional[str] = None
    session: Optional[Session] = None
    skills: Optional[Union[str, List[str]]] = None
    tags: Optional[List[str]] = None
