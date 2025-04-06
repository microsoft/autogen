# datamodel/eval.py
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Sequence, Any
from uuid import UUID, uuid4 
from pydantic import BaseModel 
from sqlmodel import Field 

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
    score: float
    reason: str
    max_value: float  
    min_value: float  


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

 