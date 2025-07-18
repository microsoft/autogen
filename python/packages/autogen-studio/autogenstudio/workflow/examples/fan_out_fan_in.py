"""
Fan-out/Fan-in workflow example: broadcast -> (double, square, add_ten) -> sum
"""

import asyncio
from typing import Any, Dict
from pydantic import BaseModel

from autogenstudio.workflow import Workflow, WorkflowRunner, WorkflowMetadata, StepMetadata
from autogenstudio.workflow.steps import FunctionStep
from autogenstudio.workflow.core._models import Context


# Define data models
class NumberInput(BaseModel):
    value: int


class NumberOutput(BaseModel):
    result: int


class SumOutput(BaseModel):
    total: int


# Define step functions
async def broadcast_input(input_data: NumberInput, context: Context) -> NumberOutput:
    """Pass through the input to multiple downstream steps."""
    print(f"Broadcast step - input_data: {input_data}, context state keys: {list(context.state.keys())}")
    result = input_data.value
    
    print(f"Broadcast step - result: {result} (will be forwarded to parallel steps)")
    return NumberOutput(result=result)


async def double_number(input_data: NumberOutput, context: Context) -> NumberOutput:
    """Double a number."""
    print(f"Double step - input_data: {input_data}, context state keys: {list(context.state.keys())}")
    await asyncio.sleep(0.1)  # Simulate some work
    
    # Use the direct input from broadcast step
    value = input_data.result
    
    result = value * 2
    print(f"Double step - using value: {value}, result: {result}")
    
    # Store result in context for fan-in step
    context.set('double_result', result)
    
    return NumberOutput(result=result)


async def square_number(input_data: NumberOutput, context: Context) -> NumberOutput:
    """Square a number."""
    print(f"Square step - input_data: {input_data}, context state keys: {list(context.state.keys())}")
    await asyncio.sleep(0.1)  # Simulate some work
    
    # Use the direct input from broadcast step
    value = input_data.result
    
    result = value ** 2
    print(f"Square step - using value: {value}, result: {result}")
    
    # Store result in context for fan-in step
    context.set('square_result', result)
    
    return NumberOutput(result=result)


async def add_ten(input_data: NumberOutput, context: Context) -> NumberOutput:
    """Add 10 to a number."""
    print(f"Add_ten step - input_data: {input_data}, context state keys: {list(context.state.keys())}")
    await asyncio.sleep(0.1)  # Simulate some work
    
    # Use the direct input from broadcast step
    value = input_data.result
    
    result = value + 10
    print(f"Add_ten step - using value: {value}, result: {result}")
    
    # Store result in context for fan-in step
    context.set('add_ten_result', result)
    
    return NumberOutput(result=result)


async def sum_results(input_data: NumberOutput, context: Context) -> SumOutput:
    """Sum multiple numbers from parallel steps using shared context."""
    print(f"Sum step - input_data: {input_data}, context state keys: {list(context.state.keys())}")
    
    # Collect results from shared context (cleaner than automatic output storage)
    double_result = context.get('double_result', 0)
    square_result = context.get('square_result', 0) 
    add_ten_result = context.get('add_ten_result', 0)
    
    results = [double_result, square_result, add_ten_result]
    total = sum(results)
    
    print(f"Sum step - collected from context: double={double_result}, square={square_result}, add_ten={add_ten_result}")
    print(f"Sum step - total: {total}")
    
    # Store final summary in context
    context.set('fan_in_summary', {
        'inputs': {'double': double_result, 'square': square_result, 'add_ten': add_ten_result},
        'total': total
    })
    
    return SumOutput(total=total)


async def main():
    """Run the fan-out/fan-in workflow example."""
    
    print("=== Fan-out/Fan-in Workflow Example ===")
    print("Expected: 5 -> broadcast(5) -> parallel[double(10), square(25), add_ten(15)] -> sum(50)")
    
    # Create steps
    broadcast_step = FunctionStep(
        step_id="broadcast",
        metadata=StepMetadata(name="Broadcast Input"),
        input_type=NumberInput,
        output_type=NumberOutput,
        func=broadcast_input
    )
    
    double_step = FunctionStep(
        step_id="double",
        metadata=StepMetadata(name="Double Number"),
        input_type=NumberOutput,  # Takes NumberOutput from broadcast
        output_type=NumberOutput,
        func=double_number
    )
    
    square_step = FunctionStep(
        step_id="square",
        metadata=StepMetadata(name="Square Number"),
        input_type=NumberOutput,  # Takes NumberOutput from broadcast
        output_type=NumberOutput,
        func=square_number
    )
    
    add_ten_step = FunctionStep(
        step_id="add_ten",
        metadata=StepMetadata(name="Add Ten"),
        input_type=NumberOutput,  # Takes NumberOutput from broadcast
        output_type=NumberOutput,
        func=add_ten
    )
    
    sum_step = FunctionStep(
        step_id="sum",
        metadata=StepMetadata(name="Sum Results"),
        input_type=NumberOutput,  # Takes NumberOutput from parallel steps
        output_type=SumOutput,
        func=sum_results
    )
    
    # Create workflow
    workflow = Workflow(
        metadata=WorkflowMetadata(name="Fan-out Fan-in Example")
    )
    
    # Add steps
    workflow.add_step(broadcast_step)
    workflow.add_step(double_step)
    workflow.add_step(square_step) 
    workflow.add_step(add_ten_step)
    workflow.add_step(sum_step)
    
    # Set up the fan-out pattern: broadcast -> all three parallel operations
    workflow.set_start_step("broadcast")
    workflow.add_edge("broadcast", "double")
    workflow.add_edge("broadcast", "square") 
    workflow.add_edge("broadcast", "add_ten")
    
    # Set up the fan-in pattern: all three operations -> sum
    workflow.add_edge("double", "sum")
    workflow.add_edge("square", "sum") 
    workflow.add_edge("add_ten", "sum")
    
    # Set end step
    workflow.add_end_step("sum")
    
    # Run workflow
    runner = WorkflowRunner(max_concurrent_steps=3)
    initial_input = {"value": 5}
    
    print(f"\nRunning workflow with input: {initial_input}")
    execution = await runner.run(workflow, initial_input)
    
    # Print results
    print("\n=== Results ===")
    for step_id, step_exec in execution.step_executions.items():
        print(f"{step_id}: {step_exec.output_data}")
    
    print(f"\nFinal result: {execution.step_executions['sum'].output_data}")
    print(f"Expected: {{'total': 50}}")


if __name__ == "__main__":
    asyncio.run(main())
