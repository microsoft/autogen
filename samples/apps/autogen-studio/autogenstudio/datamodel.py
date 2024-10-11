from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Union

from sqlalchemy import ForeignKey, Integer, orm
from sqlmodel import (
    JSON,
    Column,
    DateTime,
    Field,
    Relationship,
    SQLModel,
    func,
)
from sqlmodel import (
    Enum as SqlEnum,
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

# pylint: disable=protected-access


class MessageMeta(SQLModel, table=False):
    task: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    summary_method: Optional[str] = "last"
    files: Optional[List[dict]] = None
    time: Optional[datetime] = None
    log: Optional[List[dict]] = None
    usage: Optional[List[dict]] = None


class Message(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # pylint: disable=not-callable
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )  # pylint: disable=not-callable
    user_id: Optional[str] = None
    role: str
    content: str
    session_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("session.id", ondelete="CASCADE"))
    )
    connection_id: Optional[str] = None
    meta: Optional[Union[MessageMeta, dict]] = Field(default={}, sa_column=Column(JSON))


class Session(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # pylint: disable=not-callable
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )  # pylint: disable=not-callable
    user_id: Optional[str] = None
    workflow_id: Optional[int] = Field(default=None, foreign_key="workflow.id")
    name: Optional[str] = None
    description: Optional[str] = None


class AgentSkillLink(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    agent_id: int = Field(default=None, primary_key=True, foreign_key="agent.id")
    skill_id: int = Field(default=None, primary_key=True, foreign_key="skill.id")


class AgentModelLink(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    agent_id: int = Field(default=None, primary_key=True, foreign_key="agent.id")
    model_id: int = Field(default=None, primary_key=True, foreign_key="model.id")


class Skill(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # pylint: disable=not-callable
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )  # pylint: disable=not-callable
    user_id: Optional[str] = None
    version: Optional[str] = "0.0.1"
    name: str
    content: str
    description: Optional[str] = None
    secrets: Optional[List[dict]] = Field(default_factory=list, sa_column=Column(JSON))
    libraries: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    agents: List["Agent"] = Relationship(back_populates="skills", link_model=AgentSkillLink)


class LLMConfig(SQLModel, table=False):
    """Data model for LLM Config for AutoGen"""

    config_list: List[Any] = Field(default_factory=list)
    temperature: float = 0
    cache_seed: Optional[Union[int, None]] = None
    timeout: Optional[int] = None
    max_tokens: Optional[int] = 2048
    extra_body: Optional[dict] = None


class ModelTypes(str, Enum):
    openai = "open_ai"
    cerebras = "cerebras"
    google = "google"
    azure = "azure"
    anthropic = "anthropic"
    mistral = "mistral"
    together = "together"
    groq = "groq"


class Model(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # pylint: disable=not-callable
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )  # pylint: disable=not-callable
    user_id: Optional[str] = None
    version: Optional[str] = "0.0.1"
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    api_type: ModelTypes = Field(default=ModelTypes.openai, sa_column=Column(SqlEnum(ModelTypes)))
    api_version: Optional[str] = None
    description: Optional[str] = None
    agents: List["Agent"] = Relationship(back_populates="models", link_model=AgentModelLink)


class CodeExecutionConfigTypes(str, Enum):
    local = "local"
    docker = "docker"
    none = "none"


class AgentConfig(SQLModel, table=False):
    name: Optional[str] = None
    human_input_mode: str = "NEVER"
    max_consecutive_auto_reply: int = 10
    system_message: Optional[str] = None
    is_termination_msg: Optional[Union[bool, str, Callable]] = None
    code_execution_config: CodeExecutionConfigTypes = Field(
        default=CodeExecutionConfigTypes.local, sa_column=Column(SqlEnum(CodeExecutionConfigTypes))
    )
    default_auto_reply: Optional[str] = ""
    description: Optional[str] = None
    llm_config: Optional[Union[LLMConfig, bool]] = Field(default=False, sa_column=Column(JSON))

    admin_name: Optional[str] = "Admin"
    messages: Optional[List[Dict]] = Field(default_factory=list)
    max_round: Optional[int] = 100
    speaker_selection_method: Optional[str] = "auto"
    allow_repeat_speaker: Optional[Union[bool, List["AgentConfig"]]] = True


class AgentType(str, Enum):
    assistant = "assistant"
    userproxy = "userproxy"
    groupchat = "groupchat"


class WorkflowAgentType(str, Enum):
    sender = "sender"
    receiver = "receiver"
    planner = "planner"
    sequential = "sequential"


class WorkflowAgentLink(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    workflow_id: int = Field(default=None, primary_key=True, foreign_key="workflow.id")
    agent_id: int = Field(default=None, primary_key=True, foreign_key="agent.id")
    agent_type: WorkflowAgentType = Field(
        default=WorkflowAgentType.sender,
        sa_column=Column(SqlEnum(WorkflowAgentType), primary_key=True),
    )
    sequence_id: Optional[int] = Field(default=0, primary_key=True)


class AgentLink(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    parent_id: Optional[int] = Field(default=None, foreign_key="agent.id", primary_key=True)
    agent_id: Optional[int] = Field(default=None, foreign_key="agent.id", primary_key=True)


class Agent(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # pylint: disable=not-callable
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )  # pylint: disable=not-callable
    user_id: Optional[str] = None
    version: Optional[str] = "0.0.1"
    type: AgentType = Field(default=AgentType.assistant, sa_column=Column(SqlEnum(AgentType)))
    config: Union[AgentConfig, dict] = Field(default_factory=AgentConfig, sa_column=Column(JSON))
    skills: List[Skill] = Relationship(back_populates="agents", link_model=AgentSkillLink)
    models: List[Model] = Relationship(back_populates="agents", link_model=AgentModelLink)
    workflows: List["Workflow"] = Relationship(link_model=WorkflowAgentLink, back_populates="agents")
    parents: List["Agent"] = Relationship(
        back_populates="agents",
        link_model=AgentLink,
        sa_relationship_kwargs=dict(
            primaryjoin="Agent.id==AgentLink.agent_id",
            secondaryjoin="Agent.id==AgentLink.parent_id",
        ),
    )
    agents: List["Agent"] = Relationship(
        back_populates="parents",
        link_model=AgentLink,
        sa_relationship_kwargs=dict(
            primaryjoin="Agent.id==AgentLink.parent_id",
            secondaryjoin="Agent.id==AgentLink.agent_id",
        ),
    )
    task_instruction: Optional[str] = None


class WorkFlowType(str, Enum):
    autonomous = "autonomous"
    sequential = "sequential"


class WorkFlowSummaryMethod(str, Enum):
    last = "last"
    none = "none"
    llm = "llm"


class Workflow(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # pylint: disable=not-callable
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()),
    )  # pylint: disable=not-callable
    user_id: Optional[str] = None
    version: Optional[str] = "0.0.1"
    name: str
    description: str
    agents: List[Agent] = Relationship(back_populates="workflows", link_model=WorkflowAgentLink)
    type: WorkFlowType = Field(default=WorkFlowType.autonomous, sa_column=Column(SqlEnum(WorkFlowType)))
    summary_method: Optional[WorkFlowSummaryMethod] = Field(
        default=WorkFlowSummaryMethod.last,
        sa_column=Column(SqlEnum(WorkFlowSummaryMethod)),
    )
    sample_tasks: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))


class Response(SQLModel):
    message: str
    status: bool
    data: Optional[Any] = None


class SocketMessage(SQLModel, table=False):
    connection_id: str
    data: Dict[str, Any]
    type: str
