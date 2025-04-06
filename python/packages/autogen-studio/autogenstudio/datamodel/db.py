# defines how core data types in autogenstudio are serialized and stored in the database

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from autogen_core import ComponentModel
from pydantic import ConfigDict, SecretStr, field_validator 
from sqlalchemy import ForeignKey, Integer
from sqlmodel import JSON, Column, DateTime, Field, SQLModel, func
 

from .types import (
    GalleryComponents,
    GalleryConfig,
    GalleryMetadata,
    MessageConfig,
    MessageMeta,
    SettingsConfig,
    TeamResult,
)

from .eval import (
    EvalTask, 
    EvalJudgeCriteria, 
    EvalRunResult, 
    EvalScore, 
    EvalRunStatus
)
from autogen_core import ComponentModel

class BaseDBModel(SQLModel, table=False):
    """
    Base model with common fields for all database tables.
    Not a table itself - meant to be inherited by concrete model classes.
    """
    __abstract__ = True
    
    # Common fields present in all database tables
    id: Optional[int] = Field(
        default=None, 
        primary_key=True
    )
    
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_type=DateTime(timezone=True), # type: ignore[assignment]
        sa_column_kwargs={
            "server_default": func.now(),
            "nullable": True
        }
    )
    
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_type=DateTime(timezone=True), # type: ignore[assignment]
        sa_column_kwargs={
            "onupdate": func.now(),
            "nullable": True
        }
    )
    
    user_id: Optional[str] = None
    version: Optional[str] = "0.0.1"
     


class Team(BaseDBModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True} 
    component: Union[ComponentModel, dict] = Field(sa_column=Column(JSON))


class Message(BaseDBModel, table=True): 
    __table_args__ = {"sqlite_autoincrement": True}

    config: Union[MessageConfig, dict] = Field(
        default_factory=lambda: MessageConfig(source="", content=""), sa_column=Column(JSON)
    )
    session_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("session.id", ondelete="NO ACTION"))
    )
    run_id: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("run.id", ondelete="CASCADE")))

    message_meta: Optional[Union[MessageMeta, dict]] = Field(default={}, sa_column=Column(JSON))


class Session(BaseDBModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    team_id: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("team.id", ondelete="CASCADE")))
    name: Optional[str] = None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, value: Union[str, datetime]) -> datetime:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value


class RunStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"
    STOPPED = "stopped"


class Run(BaseDBModel, table=True):
    """Represents a single execution run within a session"""

    __table_args__ = {"sqlite_autoincrement": True}

     
    session_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("session.id", ondelete="CASCADE"), nullable=False)
    )
    status: RunStatus = Field(default=RunStatus.CREATED)

    # Store the original user task
    task: Union[MessageConfig, dict] = Field(
        default_factory=lambda: MessageConfig(source="", content=""), sa_column=Column(JSON)
    )

    # Store TeamResult which contains TaskResult
    team_result: Union[TeamResult, dict] = Field(default=None, sa_column=Column(JSON))

    error_message: Optional[str] = None
    version: Optional[str] = "0.0.1"
    messages: Union[List[Message], List[dict]] = Field(default_factory=list, sa_column=Column(JSON))

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})  # type: ignore[call-arg]
    user_id: Optional[str] = None


class Gallery(BaseDBModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
    
    config: Union[GalleryConfig, dict] = Field(
        default_factory=lambda: GalleryConfig(
            id="",
            name="",
            metadata=GalleryMetadata(author="", version=""),
            components=GalleryComponents(agents=[], models=[], tools=[], terminations=[], teams=[]),
        ),
        sa_column=Column(JSON),
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            SecretStr: lambda v: v.get_secret_value(),  # Add this line
        }
    )  # type: ignore[call-arg]


class Settings(BaseDBModel, table=True):
    __table_args__ = {"sqlite_autoincrement": True}
     
    config: Union[SettingsConfig, dict] = Field(default_factory=SettingsConfig, sa_column=Column(JSON))

# --- Evaluation system database models ---

class EvalTaskDB(BaseDBModel, table=True):
    """Database model for storing evaluation tasks."""
    __table_args__ = {"sqlite_autoincrement": True}
    
    name: str = "Unnamed Task"
    description: str = ""
    config: Union[EvalTask, dict] = Field(sa_column=Column(JSON)) 


class EvalCriteriaDB(BaseDBModel, table=True):
    """Database model for storing evaluation criteria."""
    __table_args__ = {"sqlite_autoincrement": True}
    
    name: str = "Unnamed Criteria"
    description: str = ""
    config: Union[EvalJudgeCriteria, dict] = Field(sa_column=Column(JSON)) 


class EvalRunDB(BaseDBModel, table=True):
    """Database model for tracking evaluation runs."""
    __table_args__ = {"sqlite_autoincrement": True}
    
    name: str = "Unnamed Evaluation Run"
    description: str = ""
    
    # References to related components
    task_id: Optional[int] = Field(
        default=None, 
        sa_column=Column(Integer, ForeignKey("evaltaskdb.id", ondelete="SET NULL"))
    )
    
    # Serialized configurations for runner and judge
    runner_config: Union[ComponentModel, dict] = Field(sa_column=Column(JSON))
    judge_config: Union[ComponentModel, dict] = Field(sa_column=Column(JSON))
    
    # List of criteria IDs or embedded criteria configs
    criteria_configs: List[Union[EvalJudgeCriteria, dict]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    
    # Run status and timing information
    status: EvalRunStatus = Field(default=EvalRunStatus.PENDING)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    
    # Results (updated as they become available)
    run_result: Union[EvalRunResult, dict] = Field(
        default=None, sa_column=Column(JSON)
    )
    
    score_result: Union[EvalScore, dict] = Field(
        default=None, sa_column=Column(JSON)
    )
    
    # Additional metadata
    error_message: Optional[str] = None 