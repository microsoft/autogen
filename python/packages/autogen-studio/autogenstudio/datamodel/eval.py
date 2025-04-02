# datamodel/eval.py
from datetime import datetime
from enum import Enum
from os import error
from typing import Dict, List, Optional, Sequence, Union, Any
from unittest import runner
from uuid import UUID, uuid4 
from flask import Config
from polars import date
from pydantic import BaseModel 
from sqlmodel import JSON, Column, Field 

from .db import BaseDBModel
from autogen_agentchat.messages import ChatMessage
from autogen_core.models import LLMMessage
from autogen_core import Image 
from autogen_agentchat.base import TaskResult

class EvalTask(BaseModel):
    """Definition of a task to be evaluated."""
    task_id:  UUID | str = Field(default_factory=uuid4)  
    input: str | Sequence[str | Image]  
    name: str = ""
    description: str = "" 
    expected_outputs: Optional[List[Any]] = None
    metadata: Dict[str, Any] = {}

class EvalRunResult(BaseModel):
    """Result of an evaluation run."""
    result: TaskResult | None = None
    status: bool = False 
    start_time: Optional[datetime] = Field(default=datetime.now())
    end_time: Optional[datetime] = None 
    error: Optional[str] = None
    

class EvalDimensionScore(BaseModel):
    """Score for a single evaluation dimension."""
    dimension: str
    score: Optional[float] = None
    reason: Optional[str] = None
    max_value: float = 10.0
    min_value: float = 0.0
    metadata: Dict[str, Any] = {}


class EvalScore(BaseModel):
    """Composite score from evaluation."""
    overall_score: Optional[float] = None
    dimension_scores: List[EvalDimensionScore] = []
    reason: Optional[str] = None
    max_value: float = 10.0 
    min_value: float = 0.0
    metadata: Dict[str, Any] = {}

class EvalJudgeCriteria(BaseModel):
    """Criteria for judging evaluation results."""
    dimension: str
    prompt: str
    max_value: float = 10.0
    min_value: float = 0.0
    metadata: Dict[str, Any] = {}



class EvalRunStatus(str, Enum):
    """Status of an evaluation run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class EvalResult(BaseModel):
    """Result of an evaluation run."""
    task_id: UUID | str
    # runner_id: UUID | str
    status: EvalRunStatus = EvalRunStatus.PENDING
    start_time: Optional[datetime] = Field(default=datetime.now())
    end_time: Optional[datetime] = None  



# # --- SQLModel tables for database storage ---

# class EvalRunner(BaseDBModel, table=True):
#     """Configuration for an evaluation runner.""" 
#     __table_args__ = {"sqlite_autoincrement": True}
    
#     name: str = "Unnamed Run"
#     description: str = ""
#     config: Dict[str, Any] = {}  # Team config or model config
#     config_type: str = "team"  # "team", "model", etc.
#     metadata: Dict[str, Any] = {}

 
# class EvalConfig(BaseDBModel, table=True):
#     """Details on an Eval Run."""
#     __table_args__ = {"sqlite_autoincrement": True}
    
#     name: str = ""
#     description: str = ""
#     tasks: Dict[str, EvalTask] = Field(default_factory=dict, sa_column=Column(JSON))
#     runner: Union[EvalRunner, dict] = Field(default_factory=lambda: EvalRunner(), sa_column=Column(JSON))
#     judge_criteria: List[EvalJudgeCriteria] = Field(default_factory=list, sa_column=Column(JSON))
#     metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


# class EvalRun(BaseDBModel, table=True):
#     """A run of an experiment."""
#     __table_args__ = {"sqlite_autoincrement": True}
    
#     eval_id: int = Field(index=True)
#     status: EvalRunStatus = Field(default=EvalRunStatus.PENDING)
#     start_time: Optional[datetime] = None
#     end_time: Optional[datetime] = None
#     metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


 