"""
Test script to verify workflow cancellation functionality.
"""

import asyncio
import time
from pydantic import BaseModel
from autogenstudio.workflow.core import Workflow, WorkflowRunner, StepMetadata, WorkflowMetadata
from autogenstudio.workflow.steps import FunctionStep
from autogen_core import CancellationToken


class TestInput(BaseModel):
    message: str


class TestOutput(BaseModel):
    result: str


async def slow_step(input_data: TestInput, context) -> TestOutput:
    """A step that takes time to simulate long-running operations."""
    print(f"Starting slow step with: {input_data.message}")
    
    # Simulate work that takes time
    for i in range(10):
        print(f"  Working... {i+1}/10")
        await asyncio.sleep(0.5)  # Shorter delay to show cancellation faster
    
    result = f"Completed: {input_data.message}"
    print(f"Step completed: {result}")
    return TestOutput(result=result)


async def quick_step(input_data: TestOutput, context) -> TestOutput:
    """A quick step that should complete before cancellation."""
    print(f"Quick step processing: {input_data.result}")
    
    result = f"Quick: {input_data.result}"
    print(f"Quick step completed: {result}")
    return TestOutput(result=result)


async def very_slow_step(input_data: TestOutput, context) -> TestOutput:
    """A very slow step that should be prevented from starting when cancelled."""
    print(f"Very slow step starting with: {input_data.result}")
    
    # This step should never start if cancellation is working properly
    for i in range(20):
        print(f"  Very slow working... {i+1}/20")
        await asyncio.sleep(0.3)
    
    result = f"Very slow completed: {input_data.result}"
    print(f"Very slow step completed: {result}")
    return TestOutput(result=result)


def create_test_workflow():
    """Create a test workflow with slow and quick steps."""
    
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Cancellation Test Workflow",
            description="Test workflow cancellation with slow and quick steps",
            version="1.0.0"
        )
    )
    
    # Create steps
    slow_step_component = FunctionStep(
        step_id="slow", 
        metadata=StepMetadata(name="Slow Step"),
        input_type=TestInput,
        output_type=TestOutput,
        func=slow_step
    )
    
    quick_step_component = FunctionStep(
        step_id="quick",
        metadata=StepMetadata(name="Quick Step"),
        input_type=TestOutput,
        output_type=TestOutput,
        func=quick_step
    )
    
    very_slow_step_component = FunctionStep(
        step_id="very_slow",
        metadata=StepMetadata(name="Very Slow Step"),
        input_type=TestOutput,
        output_type=TestOutput,
        func=very_slow_step
    )
    
    # Add steps
    workflow.add_step(slow_step_component)
    workflow.add_step(quick_step_component)
    workflow.add_step(very_slow_step_component)
    
    # Add edges: slow -> quick -> very_slow
    workflow.add_edge("slow", "quick")
    workflow.add_edge("quick", "very_slow")
    
    # Set workflow structure
    workflow.set_start_step("slow")
    workflow.add_end_step("very_slow")
    
    return workflow


async def test_cancellation():
    """Test workflow cancellation."""
    
    print("=== Testing Workflow Cancellation ===\n")
    
    workflow = create_test_workflow()
    runner = WorkflowRunner()
    
    # Create cancellation token
    cancellation_token = CancellationToken()
    
    # Start workflow execution in background
    print("Starting workflow execution...")
    execution_task = asyncio.create_task(
        runner.run(workflow, {"message": "Hello World"}, cancellation_token)
    )
    
    # Wait a bit then cancel
    print("Waiting 2 seconds before cancelling...")
    await asyncio.sleep(2)
    
    print("Cancelling workflow...")
    cancellation_token.cancel()
    
    try:
        # Wait for execution to complete (should be cancelled)
        result = await execution_task
        print(f"Workflow completed: {result}")
    except RuntimeError as e:
        print(f"Workflow was cancelled as expected: {e}")
    
    print("\n=== Test completed ===")


async def test_stream_cancellation():
    """Test workflow cancellation with streaming events."""
    
    print("\n=== Testing Workflow Cancellation with Streaming ===\n")
    
    workflow = create_test_workflow()
    runner = WorkflowRunner()
    
    # Create cancellation token
    cancellation_token = CancellationToken()
    
    print("Starting workflow execution with streaming...")
    
    # Start workflow execution in background
    async def run_with_stream():
        async for event in runner.run_stream(workflow, {"message": "Stream Test"}, cancellation_token):
            print(f"Event: {event.event_type} - {event.timestamp}")
            if hasattr(event, 'step_id'):
                print(f"  Step: {event.step_id}")
            if hasattr(event, 'reason'):
                print(f"  Reason: {event.reason}")
    
    stream_task = asyncio.create_task(run_with_stream())
    
    # Wait a bit then cancel
    print("Waiting 1.5 seconds before cancelling...")
    await asyncio.sleep(1.5)
    
    print("Cancelling workflow...")
    cancellation_token.cancel()
    
    try:
        await stream_task
    except Exception as e:
        print(f"Stream completed with: {e}")
    
    print("\n=== Streaming test completed ===")


if __name__ == "__main__":
    asyncio.run(test_cancellation())
    asyncio.run(test_stream_cancellation()) 