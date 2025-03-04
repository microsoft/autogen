# defines how core data types in autogenstudio are serialized and stored in the database

from datetime import datetime
from enum import Enum
from typing import List, Optional, Union
from uuid import UUID, uuid4

from autogen_core import ComponentModel
from pydantic import ConfigDict
from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy import ForeignKey, Integer, String
from sqlmodel import JSON, Column, DateTime, Field, SQLModel, func

from .types import GalleryConfig, MessageConfig, MessageMeta, SettingsConfig, TeamResult


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
    component: Union[ComponentModel, dict] = Field(sa_column=Column(JSON))


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
    config: Union[MessageConfig, dict] = Field(default_factory=MessageConfig, sa_column=Column(JSON))
    session_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("session.id", ondelete="CASCADE"))
    )
    run_id: Optional[UUID] = Field(
        default=None, sa_column=Column(SQLAlchemyUUID, ForeignKey("run.id", ondelete="CASCADE"))
    )

    message_meta: Optional[Union[MessageMeta, dict]] = Field(default={}, sa_column=Column(JSON))


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
    team_id: Optional[int] = Field(default=None, sa_column=Column(Integer, ForeignKey("team.id", ondelete="CASCADE")))
    name: Optional[str] = None


class RunStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"
    STOPPED = "stopped"


class Run(SQLModel, table=True):
    """Represents a single execution run within a session"""

    __table_args__ = {"sqlite_autoincrement": True}

    id: UUID = Field(default_factory=uuid4, sa_column=Column(SQLAlchemyUUID, primary_key=True, index=True, unique=True))
    created_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    session_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("session.id", ondelete="CASCADE"), nullable=False)
    )
    status: RunStatus = Field(default=RunStatus.CREATED)

    # Store the original user task
    task: Union[MessageConfig, dict] = Field(default_factory=MessageConfig, sa_column=Column(JSON))

    # Store TeamResult which contains TaskResult
    team_result: Union[TeamResult, dict] = Field(default=None, sa_column=Column(JSON))

    error_message: Optional[str] = None
    version: Optional[str] = "0.0.1"
    messages: Union[List[Message], List[dict]] = Field(default_factory=list, sa_column=Column(JSON))

    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda v: v.isoformat()})
    user_id: Optional[str] = None


class Gallery(SQLModel, table=True):
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
    config: Union[GalleryConfig, dict] = Field(default_factory=GalleryConfig, sa_column=Column(JSON))

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat(), UUID: str})


class Settings(SQLModel, table=True):
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
    config: Union[SettingsConfig, dict] = Field(default_factory=SettingsConfig, sa_column=Column(JSON))
