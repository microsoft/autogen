from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from autogen_agentchat.base import TaskResult
from pydantic import BaseModel


class ModelTypes(str, Enum):
    OPENAI = "OpenAIChatCompletionClient"


class ToolTypes(str, Enum):
    PYTHON_FUNCTION = "PythonFunction"


class AgentTypes(str, Enum):
    ASSISTANT = "AssistantAgent"
    USERPROXY = "UserProxyAgent"
    MULTIMODAL_WEBSURFER = "MultimodalWebSurfer"


class TeamTypes(str, Enum):
    ROUND_ROBIN = "RoundRobinGroupChat"
    SELECTOR = "SelectorGroupChat"


class TerminationTypes(str, Enum):
    MAX_MESSAGES = "MaxMessageTermination"
    STOP_MESSAGE = "StopMessageTermination"
    TEXT_MENTION = "TextMentionTermination"
    COMBINATION = "CombinationTermination"


class ComponentTypes(str, Enum):
    TEAM = "team"
    AGENT = "agent"
    MODEL = "model"
    TOOL = "tool"
    TERMINATION = "termination"


class BaseConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    version: str = "1.0.0"
    component_type: ComponentTypes


class MessageConfig(BaseModel):
    source: str
    content: str
    message_type: Optional[str] = "text"


class ModelConfig(BaseConfig):
    model: str
    model_type: ModelTypes
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    component_type: ComponentTypes = ComponentTypes.MODEL


class ToolConfig(BaseConfig):
    name: str
    description: str
    content: str
    tool_type: ToolTypes
    component_type: ComponentTypes = ComponentTypes.TOOL


class AgentConfig(BaseConfig):
    name: str
    agent_type: AgentTypes
    system_message: Optional[str] = None
    model_client: Optional[ModelConfig] = None
    tools: Optional[List[ToolConfig]] = None
    description: Optional[str] = None
    component_type: ComponentTypes = ComponentTypes.AGENT
    headless: Optional[bool] = None
    logs_dir: Optional[str] = None
    to_save_screenshots: Optional[bool] = None
    use_ocr: Optional[bool] = None
    animate_actions: Optional[bool] = None


class TerminationConfig(BaseConfig):
    termination_type: TerminationTypes
    # Fields for basic terminations
    max_messages: Optional[int] = None
    text: Optional[str] = None
    # Fields for combinations
    operator: Optional[Literal["and", "or"]] = None
    conditions: Optional[List["TerminationConfig"]] = None
    component_type: ComponentTypes = ComponentTypes.TERMINATION


class TeamConfig(BaseConfig):
    name: str
    participants: List[AgentConfig]
    team_type: TeamTypes
    model_client: Optional[ModelConfig] = None
    selector_prompt: Optional[str] = None
    termination_condition: Optional[TerminationConfig] = None
    component_type: ComponentTypes = ComponentTypes.TEAM


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


ComponentConfig = Union[TeamConfig, AgentConfig, ModelConfig, ToolConfig, TerminationConfig]

ComponentConfigInput = Union[str, Path, dict, ComponentConfig]
