"""
Simple Conditional Workflow Example

Demonstrates basic conditional edges with success/failure routing.
"""

import asyncio
from pydantic import BaseModel
from autogenstudio.workflow.core import Workflow, WorkflowRunner, StepMetadata, WorkflowMetadata, EdgeCondition
from autogenstudio.workflow.steps import FunctionStep


class TaskInput(BaseModel):
    task: str


class TaskResult(BaseModel):
    result: str
    success: bool


async def process_task(input_data: TaskInput, context) -> TaskResult:
    """Process a task and determine success/failure."""
    # Simple logic: tasks with "deploy" succeed, others fail
    success = "deploy" in input_data.task.lower()
    result = f"Processed: {input_data.task}"
    
    return TaskResult(result=result, success=success)


async def handle_success(input_data: TaskResult, context) -> TaskResult:
    """Handle successful tasks."""
    result = f"SUCCESS: {input_data.result} ✅"
    return TaskResult(result=result, success=True)


async def handle_failure(input_data: TaskResult, context) -> TaskResult:
    """Handle failed tasks.""" 
    result = f"RETRY: {input_data.result} 🔄"
    return TaskResult(result=result, success=True)


def create_simple_conditional_workflow():
    """Create a simple workflow with conditional success/failure routing."""
    
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Simple Conditional Workflow",
            description="Route tasks based on success/failure",
            version="1.0.0"
        )
    )
    
    # Create steps
    process_step = FunctionStep(
        step_id="process", 
        metadata=StepMetadata(name="Process Task"),
        input_type=TaskInput,
        output_type=TaskResult,
        func=process_task
    )
    
    success_step = FunctionStep(
        step_id="handle_success",
        metadata=StepMetadata(name="Handle Success"),
        input_type=TaskResult,
        output_type=TaskResult,
        func=handle_success
    )
    
    failure_step = FunctionStep(
        step_id="handle_failure",
        metadata=StepMetadata(name="Handle Failure"),
        input_type=TaskResult,
        output_type=TaskResult,
        func=handle_failure
    )
    
    # Add steps
    workflow.add_step(process_step)
    workflow.add_step(success_step)
    workflow.add_step(failure_step)
    
    # Add conditional edges
    # Route to success handler if task succeeded
    success_condition = EdgeCondition(
        type="output_based",
        field="success",
        operator="==", 
        value=True
    )
    workflow.add_edge("process", "handle_success", success_condition.model_dump())
    
    # Route to failure handler if task failed
    failure_condition = EdgeCondition(
        type="output_based",
        field="success",
        operator="==",
        value=False
    )
    workflow.add_edge("process", "handle_failure", failure_condition.model_dump())
    
    # Set workflow structure
    workflow.set_start_step("process")
    workflow.add_end_step("handle_success")
    workflow.add_end_step("handle_failure")
    
    return workflow


async def main():
    """Run the simple conditional workflow example."""
    
    workflow = create_simple_conditional_workflow()
    runner = WorkflowRunner()
    
    print("=== Simple Conditional Workflow Example ===\n")
    
    # Test cases
    test_cases = [
        {"task": "Deploy new feature"},  # Should succeed 
        {"task": "Run tests"},           # Should fail
        {"task": "Deploy hotfix"},       # Should succeed
        {"task": "Update docs"}          # Should fail
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"Test {i}: {test_input}")
        
        result = await runner.run(workflow, test_input)
        
        # Find which end step was executed
        end_step = None
        for step_id in ["handle_success", "handle_failure"]:
            if step_id in result.step_executions:
                end_step = step_id
                break
        
        if end_step:
            final_output = result.step_executions[end_step].output_data
            print(f"  → {final_output['result']}")
        else:
            print("  → No end step executed")
        
        print()


if __name__ == "__main__":
    asyncio.run(main())