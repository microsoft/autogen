# defines how core data types in autogenstudio are serialized and stored in the database

from datetime import datetime
from typing import List, Optional, Union
from sqlalchemy import ForeignKey, Integer
from sqlmodel import (
    JSON,
    Column,
    DateTime,
    Field,
    SQLModel,
    func,
    Relationship
)

from .types import ToolConfig, ModelConfig, AgentConfig, TeamConfig, MessageConfig, MessageMeta

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


# link models
class AgentToolLink(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    agent_id: int = Field(default=None, primary_key=True,
                          foreign_key="agent.id")
    tool_id: int = Field(default=None, primary_key=True, foreign_key="tool.id")


class AgentModelLink(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    agent_id: int = Field(default=None, primary_key=True,
                          foreign_key="agent.id")
    model_id: int = Field(default=None, primary_key=True,
                          foreign_key="model.id")


class TeamAgentLink(SQLModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    team_id: int = Field(default=None, primary_key=True, foreign_key="team.id")
    agent_id: int = Field(default=None, primary_key=True,
                          foreign_key="agent.id")
    sequence: Optional[int] = Field(default=0, primary_key=True)

# database models


class Tool(SQLModel, table=True):
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
    config: Union[ToolConfig, dict] = Field(
        default_factory=ToolConfig, sa_column=Column(JSON))
    agents: List["Agent"] = Relationship(
        back_populates="tools", link_model=AgentToolLink)


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
    config: Union[ModelConfig, dict] = Field(
        default_factory=ModelConfig, sa_column=Column(JSON))
    agents: List["Agent"] = Relationship(
        back_populates="models", link_model=AgentModelLink)


class Team(SQLModel, table=True):
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
    config: Union[TeamConfig, dict] = Field(
        default_factory=TeamConfig, sa_column=Column(JSON))
    agents: List["Agent"] = Relationship(
        back_populates="teams", link_model=TeamAgentLink)


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
    config: Union[AgentConfig, dict] = Field(
        default_factory=AgentConfig, sa_column=Column(JSON))
    tools: List[Tool] = Relationship(
        back_populates="agents", link_model=AgentToolLink)
    models: List[Model] = Relationship(
        back_populates="agents", link_model=AgentModelLink)
    teams: List[Team] = Relationship(
        back_populates="agents", link_model=TeamAgentLink)


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
    version: Optional[str] = "0.0.1"
    config: Union[MessageConfig, dict] = Field(
        default_factory=MessageConfig, sa_column=Column(JSON))
    session_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("session.id", ondelete="CASCADE"))
    )
    message_meta: Optional[Union[MessageMeta, dict]] = Field(
        default={}, sa_column=Column(JSON))


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
    version: Optional[str] = "0.0.1"
    team_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("team.id", ondelete="CASCADE"))
    )
