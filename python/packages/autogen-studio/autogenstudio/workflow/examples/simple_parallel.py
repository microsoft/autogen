"""
Simple parallel workflow example: parallel execution of independent steps
"""

import asyncio
from typing import Any, Dict
from pydantic import BaseModel

from autogenstudio.workflow import Workflow, WorkflowRunner, WorkflowMetadata, StepMetadata
from autogenstudio.workflow.steps import FunctionStep


# Define data models
class NumberInput(BaseModel):
    value: int


class NumberOutput(BaseModel):
    result: int


# Define step functions
async def double_number(input_data: NumberInput, context: Dict[str, Any]) -> NumberOutput:
    """Double a number."""
    print(f"Double step - input_data: {input_data}, context keys: {list(context.keys())}")
    await asyncio.sleep(0.2)  # Simulate some work
    result = input_data.value * 2
    print(f"Double step - result: {result}")
    return NumberOutput(result=result)


async def square_number(input_data: NumberInput, context: Dict[str, Any]) -> NumberOutput:
    """Square a number."""
    print(f"Square step - input_data: {input_data}, context keys: {list(context.keys())}")
    await asyncio.sleep(0.1)  # Simulate some work
    result = input_data.value ** 2
    print(f"Square step - result: {result}")
    return NumberOutput(result=result)


async def add_ten(input_data: NumberInput, context: Dict[str, Any]) -> NumberOutput:
    """Add 10 to a number."""
    print(f"Add_ten step - input_data: {input_data}, context keys: {list(context.keys())}")
    await asyncio.sleep(0.15)  # Simulate some work
    result = input_data.value + 10
    print(f"Add_ten step - result: {result}")
    return NumberOutput(result=result)


async def main():
    """Run the parallel workflow example."""
    
    print("=== Simple Parallel Workflow Example ===")
    print("Expected: All steps run in parallel with the same input (7)")
    print("  - double: 7 * 2 = 14")
    print("  - square: 7 * 7 = 49") 
    print("  - add_ten: 7 + 10 = 17")
    
    # Create steps - all independent, no dependencies
    double_step = FunctionStep(
        step_id="double",
        metadata=StepMetadata(name="Double Number"),
        input_type=NumberInput,
        output_type=NumberOutput,
        func=double_number
    )
    
    square_step = FunctionStep(
        step_id="square", 
        metadata=StepMetadata(name="Square Number"),
        input_type=NumberInput,
        output_type=NumberOutput,
        func=square_number
    )
    
    add_ten_step = FunctionStep(
        step_id="add_ten",
        metadata=StepMetadata(name="Add Ten"),
        input_type=NumberInput,
        output_type=NumberOutput,
        func=add_ten
    )
    
    # Create workflow - each step can be a start step since they're independent
    workflow = Workflow(
        metadata=WorkflowMetadata(name="Parallel Example")
    )
    
    workflow.add_step(double_step)
    workflow.add_step(square_step)
    workflow.add_step(add_ten_step)
    
    # No edges - all steps are independent and can start simultaneously
    # We'll set one as start step but run all with the same input
    workflow.set_start_step("double")
    workflow.add_end_step("double")
    workflow.add_end_step("square")
    workflow.add_end_step("add_ten")
    
    # Run workflow
    runner = WorkflowRunner(max_concurrent_steps=3)
    initial_input = {"value": 7}
    
    print(f"\nRunning workflow with input: {initial_input}")
    
    # For true parallel execution, we'd need to start all steps at once
    # This is a limitation of the current workflow design - it expects a single start step
    # Let's run each step individually to demonstrate parallel capability
    
    import time
    start_time = time.time()
    
    # Create individual tasks
    tasks = []
    for step in [double_step, square_step, add_ten_step]:
        task = asyncio.create_task(step.run(initial_input, {}))
        tasks.append((step.step_id, task))
    
    # Wait for all to complete
    results = {}
    for step_id, task in tasks:
        result = await task
        results[step_id] = result
    
    end_time = time.time()
    
    # Print results
    print("\n=== Results ===")
    for step_id, result in results.items():
        print(f"{step_id}: {result}")
    
    print(f"\nTotal execution time: {end_time - start_time:.3f} seconds")
    print("(Should be ~0.2s if truly parallel, not 0.45s if sequential)")


if __name__ == "__main__":
    asyncio.run(main())
