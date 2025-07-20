"""
Core data models for the workflow system.
"""

from typing import Any, Dict, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
import uuid
from datetime import datetime

# Type variables for generic step inputs/outputs
InputType = TypeVar("InputType", bound=BaseModel)
OutputType = TypeVar("OutputType", bound=BaseModel)


class StepStatus(str, Enum):
    """Status of a step in workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    """Status of workflow execution."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EdgeCondition(BaseModel):
    """Defines conditions for workflow edges."""
    type: str = Field(default="always", description="Type of condition: always, output_based, state_based")
    expression: Optional[str] = Field(default=None, description="Python expression to evaluate")
    field: Optional[str] = Field(default=None, description="Field to check in output or state")
    value: Optional[Any] = Field(default=None, description="Expected value")
    operator: Optional[str] = Field(default=None, description="Comparison operator: ==, !=, >, <, in, etc.")


class Edge(BaseModel):
    """Represents a connection between workflow steps."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_step: str = Field(description="Source step ID")
    to_step: str = Field(description="Target step ID")
    condition: EdgeCondition = Field(default_factory=lambda: EdgeCondition())
    
    model_config = ConfigDict(extra="forbid")


class StepExecution(BaseModel):
    """Tracks execution details of a step."""
    step_id: str
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0

    model_config = ConfigDict(extra="forbid", json_encoders={datetime: lambda v: v.isoformat()})




class WorkflowExecution(BaseModel):
    """Tracks execution of an entire workflow."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    state: Dict[str, Any] = Field(default_factory=dict)
    step_executions: Dict[str, StepExecution] = Field(default_factory=dict)
    error: Optional[str] = None

    model_config = ConfigDict(extra="forbid", json_encoders={datetime: lambda v: v.isoformat()})


class StepMetadata(BaseModel):
    """Metadata for workflow steps."""
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    max_retries: int = 0
    timeout_seconds: Optional[int] = None
    
    model_config = ConfigDict(extra="forbid")


class WorkflowMetadata(BaseModel):
    """Metadata for workflows."""
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(extra="forbid", json_encoders={datetime: lambda v: v.isoformat()})


class Context(BaseModel):
    """Simple typed context for workflow steps."""
    
    state: Dict[str, Any] = Field(default_factory=dict, description="Shared mutable workflow state")
    
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    
    @classmethod
    def from_state_ref(cls, state_dict: Dict[str, Any]) -> "Context":
        """Create Context with direct reference to state dict (no copy)."""
        # Create instance normally but then replace the state reference
        instance = cls(state={})  # Initialize with empty dict
        instance.__dict__['state'] = state_dict  # Directly set the dict reference
        return instance
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from workflow state."""
        return self.state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in workflow state."""
        self.state[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return {
            'workflow_state': self.state,
            **self.state  # Also include state values directly
        }


class WorkflowValidationResult(BaseModel):
    """Result of workflow validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    has_cycles: bool = False
    unreachable_steps: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid") 


# Workflow Event Models for Streaming
class WorkflowEventType(str, Enum):
    """Types of workflow events."""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed" 
    STEP_FAILED = "step_failed"
    EDGE_ACTIVATED = "edge_activated"


class WorkflowEvent(BaseModel):
    """Base class for workflow events."""
    event_type: WorkflowEventType
    timestamp: datetime
    workflow_id: str

    model_config = ConfigDict(extra="forbid", json_encoders={datetime: lambda v: v.isoformat()})


class WorkflowStartedEvent(WorkflowEvent):
    """Workflow execution started."""
    event_type: WorkflowEventType = WorkflowEventType.WORKFLOW_STARTED
    initial_input: Dict[str, Any]
    
    
class WorkflowCompletedEvent(WorkflowEvent):
    """Workflow execution completed successfully."""
    event_type: WorkflowEventType = WorkflowEventType.WORKFLOW_COMPLETED
    execution: WorkflowExecution


class WorkflowFailedEvent(WorkflowEvent):
    """Workflow execution failed."""
    event_type: WorkflowEventType = WorkflowEventType.WORKFLOW_FAILED
    error: str
    execution: Optional[WorkflowExecution] = None


class WorkflowCancelledEvent(WorkflowEvent):
    """Workflow execution was cancelled."""
    event_type: WorkflowEventType = WorkflowEventType.WORKFLOW_CANCELLED
    execution: WorkflowExecution
    reason: str


class StepStartedEvent(WorkflowEvent):
    """Step execution started."""
    event_type: WorkflowEventType = WorkflowEventType.STEP_STARTED
    step_id: str
    input_data: Dict[str, Any]


class StepCompletedEvent(WorkflowEvent):
    """Step execution completed successfully."""
    event_type: WorkflowEventType = WorkflowEventType.STEP_COMPLETED
    step_id: str
    output_data: Dict[str, Any]
    duration_seconds: float


class StepFailedEvent(WorkflowEvent):
    """Step execution failed."""
    event_type: WorkflowEventType = WorkflowEventType.STEP_FAILED
    step_id: str
    error: str
    duration_seconds: float


class EdgeActivatedEvent(WorkflowEvent):
    """Edge between steps activated (data flowing)."""
    event_type: WorkflowEventType = WorkflowEventType.EDGE_ACTIVATED
    from_step: str
    to_step: str
    data: Dict[str, Any] 
