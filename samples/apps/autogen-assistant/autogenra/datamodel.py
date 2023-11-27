import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional, Union
from pydantic.dataclasses import dataclass
from dataclasses import field


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

    def __post_init__(self):
        if self.msg_id is None:
            self.msg_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def dict(self):
        return {
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "root_msg_id": self.root_msg_id,
            "msg_id": self.msg_id,
            "timestamp": self.timestamp,
            "personalize": self.personalize,
            "ra": self.ra,
            "code": self.code,
            "metadata": self.metadata,
        }


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
    llm_config: Optional[LLMConfig] = None
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
class FlowConfig:
    """Data model for Flow Config for Autogen"""

    name: str
    sender: AgentFlowSpec
    receiver: Union[AgentFlowSpec, List[AgentFlowSpec]]
    type: Literal["default", "groupchat"] = "default"


@dataclass
class ChatWebRequestModel(object):
    """Data model for Chat Web Request for Web End"""

    message: Message
    flow_config: FlowConfig


@dataclass
class DeleteMessageWebRequestModel(object):
    user_id: str
    msg_id: str


@dataclass
class ClearDBWebRequestModel(object):
    user_id: str


@dataclass
class CreateSkillWebRequestModel(object):
    user_id: str
    skills: Union[str, List[str]]
