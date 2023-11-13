
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional, Union
from pydantic.dataclasses import dataclass
from dataclasses import field
@dataclass
class Message(object):
    userId: str 
    role: str
    content: str 
    rootMsgId: Optional[str] = None
    msgId: Optional[str] = None
    timestamp: Optional[datetime] = None
    use_cache: Optional[bool] = False
    personalize: Optional[bool] = False
    ra:  Optional[str] = None
    code: Optional[str] = None  
    metadata: Optional[Any] = None

    def __post_init__(self):
        if self.msgId is None:
            self.msgId = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()
    def dict(self):
        return {
            "userId": self.userId,
            "role": self.role,
            "content": self.content,
            "rootMsgId": self.rootMsgId,
            "msgId": self.msgId,
            "timestamp": self.timestamp,
            "use_cache": self.use_cache,
            "personalize": self.personalize,
            "ra": self.ra,
            "code": self.code,
            "metadata": self.metadata,
        }
@dataclass
class DeleteMessageModel(object):
    userId: str
    msgId: str

@dataclass
class ClearDBModel(object):
    userId: str    


@dataclass
class LLMConfig:
    """Data model for LLM Config for Autogen"""
    seed: int = 42
    config_list: List[Dict[str, Any]] = field(
        default_factory=list)  # a list of OpenAI API configurations
    temperature: float = 0
    use_cache: bool = True
    request_timeout: Optional[int] = None


@dataclass
class AgentConfig:
    """Data model for Agent Config for Autogen"""
    name: str
    llm_config: LLMConfig
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
    type:  Literal["default", "groupchat"] = "default"
