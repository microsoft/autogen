"""
Workflow implementation for the process system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING, TypeVar
from typing_extensions import Self
from pydantic import BaseModel, Field
import uuid
import logging
from datetime import datetime

from autogen_core import Component, ComponentModel, ComponentBase

from ._models import (
    Edge, WorkflowMetadata, WorkflowValidationResult, 
    WorkflowStatus, StepExecution, WorkflowExecution
)

if TYPE_CHECKING:
    from ..steps._step import BaseStep

logger = logging.getLogger(__name__)

# Type variable for return type chaining
WorkflowT = TypeVar("WorkflowT", bound="BaseWorkflow")


class WorkflowConfig(BaseModel):
    """Configuration for workflow serialization."""
    metadata: WorkflowMetadata
    steps: List[ComponentModel] = Field(default_factory=list, description="Serialized step component models")
    edges: List[Edge] = Field(default_factory=list)
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    start_step_id: Optional[str] = None
    end_step_ids: List[str] = Field(default_factory=list)


class BaseWorkflow(ComponentBase[BaseModel]):
    """Base class for workflows with core logic."""
    
    def __init__(
        self,
        metadata: WorkflowMetadata,
        initial_state: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ):
        """Initialize the workflow.
        
        Args:
            metadata: Workflow metadata
            initial_state: Initial workflow state
            workflow_id: Optional workflow ID
        """
        self.id = workflow_id or str(uuid.uuid4())
        self.metadata = metadata
        self.steps: Dict[str, "BaseStep"] = {}
        self.edges: List[Edge] = []
        self.initial_state = initial_state or {}
        self.start_step_id: Optional[str] = None
        self.end_step_ids: List[str] = []
    
    def add_step(self, step: "BaseStep") -> Self:
        """Add a step to the workflow.
        
        Args:
            step: Step to add
            
        Returns:
            Self for method chaining
        """
        self.steps[step.step_id] = step
        logger.debug(f"Added step {step.step_id} to workflow {self.id}")
        return self
    
    def add_edge(self, from_step: str, to_step: str, condition: Optional[Dict[str, Any]] = None) -> Self:
        """Add an edge between steps.
        
        Args:
            from_step: Source step ID
            to_step: Target step ID
            condition: Optional condition for the edge
            
        Returns:
            Self for method chaining
        """
        from ._models import EdgeCondition
        
        edge_condition = EdgeCondition(**condition) if condition else EdgeCondition()
        edge = Edge(from_step=from_step, to_step=to_step, condition=edge_condition)
        self.edges.append(edge)
        logger.debug(f"Added edge {from_step} -> {to_step} to workflow {self.id}")
        return self
    
    def set_start_step(self, step_id: str) -> Self:
        """Set the starting step for the workflow.
        
        Args:
            step_id: ID of the step to start with
            
        Returns:
            Self for method chaining
        """
        if step_id not in self.steps:
            raise ValueError(f"Step {step_id} not found in workflow")
        self.start_step_id = step_id
        logger.debug(f"Set start step to {step_id} for workflow {self.id}")
        return self
    
    def add_end_step(self, step_id: str) -> Self:
        """Add an end step to the workflow.
        
        Args:
            step_id: ID of the step that can end the workflow
            
        Returns:
            Self for method chaining
        """
        if step_id not in self.steps:
            raise ValueError(f"Step {step_id} not found in workflow")
        if step_id not in self.end_step_ids:
            self.end_step_ids.append(step_id)
        logger.debug(f"Added end step {step_id} to workflow {self.id}")
        return self
    
    def get_step_dependencies(self, step_id: str) -> List[str]:
        """Get all steps that must complete before this step can run.
        
        Args:
            step_id: Step to get dependencies for
            
        Returns:
            List of step IDs that this step depends on
        """
        return [edge.from_step for edge in self.edges if edge.to_step == step_id]
    
    def get_step_dependents(self, step_id: str) -> List[str]:
        """Get all steps that depend on this step.
        
        Args:
            step_id: Step to get dependents for
            
        Returns:
            List of step IDs that depend on this step
        """
        return [edge.to_step for edge in self.edges if edge.from_step == step_id]
    
    def get_ready_steps(self, execution: WorkflowExecution) -> List[str]:
        """Get steps that are ready to run (all dependencies completed).
        
        Args:
            execution: Current workflow execution state
            
        Returns:
            List of step IDs ready to run
        """
        ready_steps = []
        
        for step_id in self.steps:
            step_exec = execution.step_executions.get(step_id)
            
            # Skip if already running, completed, or failed
            if step_exec and step_exec.status.value in ["running", "completed", "failed"]:
                continue
            
            # Check if all dependencies are completed
            dependencies = self.get_step_dependencies(step_id)
            if not dependencies and not step_exec:
                # No dependencies and not started - ready if it's the start step
                if step_id == self.start_step_id:
                    ready_steps.append(step_id)
            elif dependencies:
                # Determine if this is a fan-in (AND) or conditional (OR) pattern
                incoming_edges = [edge for edge in self.edges if edge.to_step == step_id]
                
                # Fan-in pattern: all edges have "always" conditions
                is_fan_in = all(edge.condition.type == "always" for edge in incoming_edges)
                
                if is_fan_in:
                    # Fan-in (AND logic): all dependencies must be complete
                    all_deps_complete = True
                    for dep_id in dependencies:
                        dep_exec = execution.step_executions.get(dep_id)
                        if not dep_exec or dep_exec.status.value != "completed":
                            all_deps_complete = False
                            break
                    
                    if all_deps_complete:
                        ready_steps.append(step_id)
                else:
                    # Conditional (OR logic): any valid path makes step ready
                    step_ready = False
                    for edge in incoming_edges:
                        # Check if this specific dependency is complete
                        dep_exec = execution.step_executions.get(edge.from_step)
                        if dep_exec and dep_exec.status.value == "completed":
                            # Check if the edge condition passes
                            if self._evaluate_edge_condition(edge, execution):
                                step_ready = True
                                break
                    
                    if step_ready:
                        ready_steps.append(step_id)
        
        return ready_steps
    
    def _evaluate_edge_condition(self, edge: Edge, execution: WorkflowExecution) -> bool:
        """Evaluate if an edge condition is met.
        
        Args:
            edge: Edge to evaluate
            execution: Current execution state
            
        Returns:
            True if condition is met
        """
        condition = edge.condition
        
        if condition.type == "always":
            return True
        
        if condition.type == "output_based":
            from_step_exec = execution.step_executions.get(edge.from_step)
            if not from_step_exec or not from_step_exec.output_data:
                return False
            
            # Simple field-based condition evaluation
            if condition.field and condition.operator and condition.value is not None:
                field_value = from_step_exec.output_data.get(condition.field)
                return self._compare_values(field_value, condition.operator, condition.value)
        
        if condition.type == "state_based":
            if condition.field and condition.operator and condition.value is not None:
                field_value = execution.state.get(condition.field)
                return self._compare_values(field_value, condition.operator, condition.value)
        
        # For expression-based conditions, we'd eval the expression here
        # For now, default to True for unsupported conditions
        return True
    
    def _compare_values(self, left: Any, operator: str, right: Any) -> bool:
        """Compare two values using the given operator.
        
        Args:
            left: Left operand
            operator: Comparison operator
            right: Right operand
            
        Returns:
            Comparison result
        """
        try:
            if operator == "==":
                return left == right
            elif operator == "!=":
                return left != right
            elif operator == ">":
                return left > right
            elif operator == "<":
                return left < right
            elif operator == ">=":
                return left >= right
            elif operator == "<=":
                return left <= right
            elif operator == "in":
                return left in right
            elif operator == "not_in":
                return left not in right
            else:
                logger.warning(f"Unknown operator: {operator}")
                return True
        except Exception as e:
            logger.error(f"Error comparing values: {e}")
            return False
    
    def validate_workflow(self) -> WorkflowValidationResult:
        """Validate the workflow structure.
        
        Returns:
            Validation result with errors and warnings
        """
        result = WorkflowValidationResult(is_valid=True)
        
        # Check if workflow has steps
        if not self.steps:
            result.errors.append("Workflow has no steps")
            result.is_valid = False
        
        # Check if start step is set and exists
        if not self.start_step_id:
            result.errors.append("No start step specified")
            result.is_valid = False
        elif self.start_step_id not in self.steps:
            result.errors.append(f"Start step {self.start_step_id} not found in workflow")
            result.is_valid = False
        
        # Check if end steps exist
        if not self.end_step_ids:
            result.warnings.append("No end steps specified - workflow may run indefinitely")
        else:
            for end_step_id in self.end_step_ids:
                if end_step_id not in self.steps:
                    result.errors.append(f"End step {end_step_id} not found in workflow")
                    result.is_valid = False
        
        # Check if all edge references exist
        for edge in self.edges:
            if edge.from_step not in self.steps:
                result.errors.append(f"Edge references non-existent step: {edge.from_step}")
                result.is_valid = False
            if edge.to_step not in self.steps:
                result.errors.append(f"Edge references non-existent step: {edge.to_step}")
                result.is_valid = False
        
        # Check for cycles using DFS
        result.has_cycles, cycle_info = self._detect_cycles()
        if result.has_cycles:
            result.errors.append(f"Workflow contains cycles: {cycle_info}")
            result.is_valid = False
        
        # Check for unreachable steps
        result.unreachable_steps = self._find_unreachable_steps()
        if result.unreachable_steps:
            result.warnings.append(f"Unreachable steps found: {result.unreachable_steps}")
        
        # Check conditional edge issues
        conditional_issues = self._validate_conditional_edges()
        result.errors.extend(conditional_issues["errors"])
        result.warnings.extend(conditional_issues["warnings"])
        
        # Check for type compatibility between connected steps
        for edge in self.edges:
            if edge.from_step in self.steps and edge.to_step in self.steps:
                from_step = self.steps[edge.from_step]
                to_step = self.steps[edge.to_step]
                
                # Check type compatibility using schema-based comparison
                # This is more robust than direct type comparison, especially for dynamically created types
                types_compatible = False
                
                if hasattr(from_step.output_type, 'model_json_schema') and hasattr(to_step.input_type, 'model_json_schema'):
                    from_schema = from_step.output_type.model_json_schema()
                    to_schema = to_step.input_type.model_json_schema()
                    
                    # Consider types compatible if they have the same name and schema
                    if (from_step.output_type.__name__ == to_step.input_type.__name__ and 
                        from_schema == to_schema):
                        types_compatible = True
                        logger.debug(f"Types compatible by schema: {edge.from_step} -> {edge.to_step}")
                    else:
                        logger.debug(f"Schema mismatch for edge {edge.from_step} -> {edge.to_step}")
                        logger.debug(f"  Output schema: {from_schema}")
                        logger.debug(f"  Input schema: {to_schema}")
                else:
                    # Fallback to direct type comparison for non-Pydantic types
                    types_compatible = from_step.output_type == to_step.input_type
                    logger.debug(f"Using direct type comparison: {types_compatible}")
                
                if not types_compatible:
                    error_msg = (
                        f"Type mismatch: Step '{edge.from_step}' outputs {from_step.output_type.__name__} "
                        f"but step '{edge.to_step}' expects {to_step.input_type.__name__}"
                    )
                    result.errors.append(error_msg)
                    result.is_valid = False
        
        return result
    
    def _detect_cycles(self) -> tuple[bool, Optional[str]]:
        """Detect cycles in the workflow graph.
        
        Returns:
            Tuple of (has_cycles, cycle_description)
        """
        if not self.start_step_id:
            return False, None
        
        visited = set()
        rec_stack = set()
        
        def dfs(step_id: str, path: List[str]) -> tuple[bool, Optional[str]]:
            if step_id in rec_stack:
                cycle_start = path.index(step_id)
                cycle = " -> ".join(path[cycle_start:] + [step_id])
                return True, cycle
            
            if step_id in visited:
                return False, None
            
            visited.add(step_id)
            rec_stack.add(step_id)
            
            # Get all steps this step leads to
            next_steps = self.get_step_dependents(step_id)
            for next_step in next_steps:
                has_cycle, cycle_info = dfs(next_step, path + [step_id])
                if has_cycle:
                    return True, cycle_info
            
            rec_stack.remove(step_id)
            return False, None
        
        return dfs(self.start_step_id, [])
    
    def _find_unreachable_steps(self) -> List[str]:
        """Find steps that cannot be reached from the start step.
        
        Returns:
            List of unreachable step IDs
        """
        if not self.start_step_id:
            return list(self.steps.keys())
        
        reachable = set()
        to_visit = [self.start_step_id]
        
        while to_visit:
            current = to_visit.pop()
            if current in reachable:
                continue
            
            reachable.add(current)
            next_steps = self.get_step_dependents(current)
            to_visit.extend(next_steps)
        
        return [step_id for step_id in self.steps if step_id not in reachable]
    
    def _validate_conditional_edges(self) -> Dict[str, List[str]]:
        """Validate conditional edge logic for common issues.
        
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        # Group edges by target step to check for condition conflicts
        edges_by_target = {}
        for edge in self.edges:
            if edge.to_step not in edges_by_target:
                edges_by_target[edge.to_step] = []
            edges_by_target[edge.to_step].append(edge)
        
        # Check each step for conditional edge issues
        for step_id, incoming_edges in edges_by_target.items():
            if len(incoming_edges) > 1:
                # Multiple incoming edges - check for logical issues
                issues = self._check_multiple_conditional_edges(step_id, incoming_edges)
                errors.extend(issues["errors"])
                warnings.extend(issues["warnings"])
        
        # Check for steps with no outgoing paths
        for step_id in self.steps:
            if step_id not in self.end_step_ids:
                outgoing_edges = [e for e in self.edges if e.from_step == step_id]
                if not outgoing_edges:
                    warnings.append(f"Step '{step_id}' has no outgoing edges but is not marked as an end step")
                elif self._has_impossible_conditions(outgoing_edges):
                    errors.append(f"Step '{step_id}' has outgoing edges with contradictory conditions - some paths may be unreachable")
        
        # Check end step reachability
        unreachable_ends = self._find_unreachable_end_steps()
        for end_step in unreachable_ends:
            errors.append(f"End step '{end_step}' cannot be reached due to conditional edge constraints")
        
        return {"errors": errors, "warnings": warnings}
    
    def _check_multiple_conditional_edges(self, step_id: str, edges: List) -> Dict[str, List[str]]:
        """Check multiple incoming edges for logical conflicts."""
        errors = []
        warnings = []
        
        # Check if any edges have conflicting conditions on the same field
        field_conditions = {}
        
        for edge in edges:
            condition = edge.condition
            if condition.type in ["output_based", "state_based"] and condition.field:
                field_key = f"{condition.type}:{condition.field}"
                if field_key not in field_conditions:
                    field_conditions[field_key] = []
                field_conditions[field_key].append((edge.from_step, condition))
        
        # Look for contradictory conditions
        for field_key, conditions in field_conditions.items():
            if len(conditions) > 1:
                # Check for obvious contradictions (e.g., success=true and success=false)
                values_and_ops = [(c[1].value, c[1].operator) for c in conditions]
                
                # Check for boolean contradictions
                true_conditions = [(v, op) for v, op in values_and_ops if v is True and op == "=="]
                false_conditions = [(v, op) for v, op in values_and_ops if v is False and op == "=="]
                
                if true_conditions and false_conditions:
                    from_steps = [c[0] for c in conditions]
                    warnings.append(
                        f"Step '{step_id}' has contradictory boolean conditions from steps {from_steps} - "
                        f"only one path can execute"
                    )
        
        return {"errors": errors, "warnings": warnings}
    
    def _has_impossible_conditions(self, edges: List) -> bool:
        """Check if outgoing edges have impossible condition combinations."""
        # Simple check: if all edges have conditions that could never be true simultaneously
        # For now, just check if all conditions are on the same field with mutually exclusive values
        
        if len(edges) <= 1:
            return False
        
        # Group by field
        field_groups = {}
        for edge in edges:
            condition = edge.condition
            if condition.type == "always":
                continue  # Always conditions don't contribute to impossibility
            
            if condition.field and condition.operator and condition.value is not None:
                field_key = f"{condition.type}:{condition.field}"
                if field_key not in field_groups:
                    field_groups[field_key] = []
                field_groups[field_key].append(condition)
        
        # Check each field group for contradictions
        for field_key, conditions in field_groups.items():
            if len(conditions) == len(edges):  # All edges condition on same field
                # Check if they're all equality conditions with different values
                if all(c.operator == "==" for c in conditions):
                    values = [c.value for c in conditions]
                    if len(set(values)) == len(values):  # All different values
                        return True  # Impossible - field can't have multiple values
        
        return False
    
    def _find_unreachable_end_steps(self) -> List[str]:
        """Find end steps that cannot be reached due to conditional constraints."""
        unreachable = []
        
        for end_step_id in self.end_step_ids:
            if not self._can_reach_step_conditionally(end_step_id):
                unreachable.append(end_step_id)
        
        return unreachable
    
    def _can_reach_step_conditionally(self, target_step: str) -> bool:
        """Check if a step can be reached considering conditional edges."""
        if target_step == self.start_step_id:
            return True
        
        # Get all incoming edges to this step
        incoming_edges = [e for e in self.edges if e.to_step == target_step]
        if not incoming_edges:
            return False
        
        # Check if at least one incoming edge could potentially be satisfied
        for edge in incoming_edges:
            # If source step is reachable and condition could be satisfied
            if self._can_reach_step_conditionally(edge.from_step):
                if edge.condition.type == "always":
                    return True  # Always conditions can always be satisfied
                elif edge.condition.type in ["output_based", "state_based"]:
                    # For now, assume all conditional edges could potentially be satisfied
                    # More sophisticated analysis would require understanding the step logic
                    return True
        
        return False
    
    def get_execution_plan(self) -> Dict[str, Any]:
        """Get a visual representation of the workflow execution plan.
        
        Returns:
            Dictionary with workflow structure information
        """
        return {
            "workflow_id": self.id,
            "metadata": self.metadata.model_dump(),
            "steps": {
                step_id: step.get_schema() 
                for step_id, step in self.steps.items()
            },
            "edges": [edge.model_dump() for edge in self.edges],
            "start_step": self.start_step_id,
            "end_steps": self.end_step_ids,
            "validation": self.validate_workflow().model_dump()
        }


class Workflow(BaseWorkflow, Component[WorkflowConfig]):
    """Concrete workflow implementation with component serialization support."""
    
    component_config_schema = WorkflowConfig
    component_type = "workflow"
    component_provider_override = "autogenstudio.workflow.core.Workflow"
    
    def _to_config(self) -> WorkflowConfig:
        """Convert workflow to configuration for serialization."""
        step_configs = [step.dump_component() for step in self.steps.values()]
        
        return WorkflowConfig(
            metadata=self.metadata,
            steps=step_configs,
            edges=self.edges,
            initial_state=self.initial_state,
            start_step_id=self.start_step_id,
            end_step_ids=self.end_step_ids
        )

    @classmethod
    def _from_config(cls, config: WorkflowConfig) -> "Workflow":
        """Create workflow from configuration.
        
        Args:
            config: Workflow configuration
        """
        from ..steps._step import BaseStep
        
        workflow = cls(
            metadata=config.metadata,
            initial_state=config.initial_state
        )
        
        # Deserialize and add steps
        for step_model in config.steps:
            step = BaseStep.load_component(step_model)
            workflow.add_step(step)
        
        # Add edges
        for edge in config.edges:
            workflow.edges.append(edge)
        
        # Set start and end steps
        workflow.start_step_id = config.start_step_id
        workflow.end_step_ids = config.end_step_ids
        
        return workflow
