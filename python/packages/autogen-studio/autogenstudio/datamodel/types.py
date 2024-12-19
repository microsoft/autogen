from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from autogen_agentchat.base import TaskResult
from autogen_core.models import ModelCapabilities
from pydantic import BaseModel, Field


class ModelTypes(str, Enum):
    OPENAI = "OpenAIChatCompletionClient"
    AZUREOPENAI = "AzureOpenAIChatCompletionClient"


class ToolTypes(str, Enum):
    PYTHON_FUNCTION = "PythonFunction"


class AgentTypes(str, Enum):
    ASSISTANT = "AssistantAgent"
    USERPROXY = "UserProxyAgent"
    MULTIMODAL_WEBSURFER = "MultimodalWebSurfer"
    FILE_SURFER = "FileSurfer"
    MAGENTIC_ONE_CODER = "MagenticOneCoderAgent"


class TeamTypes(str, Enum):
    ROUND_ROBIN = "RoundRobinGroupChat"
    SELECTOR = "SelectorGroupChat"
    MAGENTIC_ONE = "MagenticOneGroupChat"


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


class BaseModelConfig(BaseConfig):
    model: str
    model_type: ModelTypes
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    component_type: ComponentTypes = ComponentTypes.MODEL
    model_capabilities: Optional[ModelCapabilities] = None


class OpenAIModelConfig(BaseModelConfig):
    model_type: ModelTypes = ModelTypes.OPENAI


class AzureOpenAIModelConfig(BaseModelConfig):
    azure_deployment: str
    model: str
    api_version: str
    azure_endpoint: str
    azure_ad_token_provider: Optional[str] = None
    api_key: Optional[str] = None
    model_type: ModelTypes = ModelTypes.AZUREOPENAI


ModelConfig = OpenAIModelConfig | AzureOpenAIModelConfig


class ToolConfig(BaseConfig):
    name: str
    description: str
    content: str
    tool_type: ToolTypes
    component_type: ComponentTypes = ComponentTypes.TOOL


class BaseAgentConfig(BaseConfig):
    name: str
    agent_type: AgentTypes
    description: Optional[str] = None
    component_type: ComponentTypes = ComponentTypes.AGENT


class AssistantAgentConfig(BaseAgentConfig):
    agent_type: AgentTypes = AgentTypes.ASSISTANT
    model_client: ModelConfig
    tools: Optional[List[ToolConfig]] = None
    system_message: Optional[str] = None


class UserProxyAgentConfig(BaseAgentConfig):
    agent_type: AgentTypes = AgentTypes.USERPROXY


class MultimodalWebSurferAgentConfig(BaseAgentConfig):
    agent_type: AgentTypes = AgentTypes.MULTIMODAL_WEBSURFER
    model_client: ModelConfig
    headless: bool = True
    logs_dir: str = None
    to_save_screenshots: bool = False
    use_ocr: bool = False
    animate_actions: bool = False
    tools: Optional[List[ToolConfig]] = None


AgentConfig = AssistantAgentConfig | UserProxyAgentConfig | MultimodalWebSurferAgentConfig


class BaseTerminationConfig(BaseConfig):
    termination_type: TerminationTypes
    component_type: ComponentTypes = ComponentTypes.TERMINATION


class MaxMessageTerminationConfig(BaseTerminationConfig):
    termination_type: TerminationTypes = TerminationTypes.MAX_MESSAGES
    max_messages: int


class TextMentionTerminationConfig(BaseTerminationConfig):
    termination_type: TerminationTypes = TerminationTypes.TEXT_MENTION
    text: str


class StopMessageTerminationConfig(BaseTerminationConfig):
    termination_type: TerminationTypes = TerminationTypes.STOP_MESSAGE


class CombinationTerminationConfig(BaseTerminationConfig):
    termination_type: TerminationTypes = TerminationTypes.COMBINATION
    operator: str
    conditions: List["TerminationConfig"]


TerminationConfig = (
    MaxMessageTerminationConfig
    | TextMentionTerminationConfig
    | CombinationTerminationConfig
    | StopMessageTerminationConfig
)


class BaseTeamConfig(BaseConfig):
    name: str
    participants: List[AgentConfig]
    team_type: TeamTypes
    termination_condition: Optional[TerminationConfig] = None
    component_type: ComponentTypes = ComponentTypes.TEAM
    max_turns: Optional[int] = None


class RoundRobinTeamConfig(BaseTeamConfig):
    team_type: TeamTypes = TeamTypes.ROUND_ROBIN


class SelectorTeamConfig(BaseTeamConfig):
    team_type: TeamTypes = TeamTypes.SELECTOR
    selector_prompt: Optional[str] = None
    model_client: ModelConfig


class MagenticOneTeamConfig(BaseTeamConfig):
    team_type: TeamTypes = TeamTypes.MAGENTIC_ONE
    model_client: ModelConfig
    max_stalls: int = 3
    final_answer_prompt: Optional[str] = None


TeamConfig = RoundRobinTeamConfig | SelectorTeamConfig | MagenticOneTeamConfig


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
