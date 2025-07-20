"""
Simple sequential workflow example: double -> square -> add_ten
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


# Define step functions
async def double_number(input_data: NumberInput, context: Context) -> NumberOutput:
    """Double a number and track operation in shared context."""
    print(f"Double step - input_data: {input_data}, context state keys: {list(context.state.keys())}")
    await asyncio.sleep(0.1)  # Simulate some work
    
    # Track the operation in shared context
    context.set('operations_performed', ['double'])
    context.set('original_input', input_data.value)
    
    value = input_data.value
    result = value * 2
    print(f"Double step - using value: {value}, result: {result}")
    print(f"Double step - stored in context: operations={context.get('operations_performed')}")
    
    return NumberOutput(result=result)


async def square_number(input_data: NumberOutput, context: Context) -> NumberOutput:
    """Square a number and update shared state tracking."""
    print(f"Square step - input_data: {input_data}, context state keys: {list(context.state.keys())}")
    await asyncio.sleep(0.1)  # Simulate some work
    
    # Read from shared context and update operation tracking
    operations = context.get('operations_performed', [])
    original_input = context.get('original_input', 'unknown')
    operations.append('square')
    context.set('operations_performed', operations)
    context.set('intermediate_results', {'after_double': input_data.result})
    
    value = input_data.result
    result = value ** 2
    
    print(f"Square step - using value: {value}, result: {result}")
    print(f"Square step - operations so far: {operations}, original input was: {original_input}")
    
    return NumberOutput(result=result)


async def add_ten(input_data: NumberOutput, context: Context) -> NumberOutput:
    """Add 10 to a number and finalize shared state."""
    print(f"Add_ten step - input_data: {input_data}, context state keys: {list(context.state.keys())}")
    await asyncio.sleep(0.1)  # Simulate some work
    
    # Read complete operation history from shared context
    operations = context.get('operations_performed', [])
    original_input = context.get('original_input', 'unknown')
    intermediate_results = context.get('intermediate_results', {})
    
    operations.append('add_ten')
    context.set('operations_performed', operations)
    
    value = input_data.result
    result = value + 10
    
    # Store final summary in context
    context.set('workflow_summary', {
        'original_input': original_input,
        'operations': operations,
        'intermediate_results': intermediate_results,
        'final_result': result
    })
    
    print(f"Add_ten step - using value: {value}, result: {result}")
    print(f"Add_ten step - complete workflow: {original_input} → {operations} → {result}")
    
    return NumberOutput(result=result)


async def main():
    """Run the sequential workflow example."""
    
    print("=== Simple Sequential Workflow Example ===")
    print("Expected: 3 -> double(6) -> square(36) -> add_ten(46)")
    print("Now with type-safe direct forwarding AND shared state tracking!")
    print("")
    
    # Create steps
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
        input_type=NumberOutput,     # Now takes NumberOutput from previous step
        output_type=NumberOutput,
        func=square_number
    )
    
    add_ten_step = FunctionStep(
        step_id="add_ten",
        metadata=StepMetadata(name="Add Ten"),
        input_type=NumberOutput,     # Now takes NumberOutput from previous step
        output_type=NumberOutput,
        func=add_ten
    )
    
    # Create workflow
    workflow = Workflow(
        metadata=WorkflowMetadata(name="Sequential Example")
    )
    
    workflow.add_step(double_step)
    workflow.add_step(square_step)
    workflow.add_step(add_ten_step)
    
    # Create sequence
    workflow.add_edge("double", "square")
    workflow.add_edge("square", "add_ten")
    
    workflow.set_start_step("double")
    workflow.add_end_step("add_ten")
    
    # Run workflow with streaming events
    runner = WorkflowRunner()
    initial_input = {"value": 3}
    
    print(f"\nRunning workflow with input: {initial_input}")
    print("\n=== Streaming Events ===")
    
    execution = None
    async for event in runner.run_stream(workflow, initial_input):
        print(f"🎯 {event.event_type}: ", end="")
        
        if event.event_type == "workflow_started":
            print(f"Started with input: {event.initial_input}")
            
        elif event.event_type == "step_started":
            print(f"Step '{event.step_id}' started with input: {event.input_data}")
            
        elif event.event_type == "step_completed":
            print(f"Step '{event.step_id}' completed in {event.duration_seconds:.2f}s")
            print(f"    Output: {event.output_data}")
            
        elif event.event_type == "step_failed":
            print(f"Step '{event.step_id}' failed in {event.duration_seconds:.2f}s: {event.error}")
            
        elif event.event_type == "edge_activated":
            print(f"Edge '{event.from_step}' → '{event.to_step}' activated")
            print(f"    Data flowing: {event.data}")
            
        elif event.event_type == "workflow_completed":
            print(f"Workflow completed successfully!")
            execution = event.execution
            
        elif event.event_type == "workflow_failed":
            print(f"Workflow failed: {event.error}")
            execution = event.execution
    
    if execution is None:
        print("❌ No final execution received!")
        return
    
    # Print results
    print("\n=== Final Results ===")
    for step_id, step_exec in execution.step_executions.items():
        print(f"{step_id}: {step_exec.output_data}")
    
    print(f"\nFinal result: {execution.step_executions['add_ten'].output_data}")
    print(f"Expected: {{'result': 46}}")
    
    # Show shared workflow state
    print("\n=== Shared Workflow State ===")
    workflow_summary = execution.state.get('workflow_summary', {})
    if workflow_summary:
        print(f"Original input: {workflow_summary.get('original_input')}")
        print(f"Operations performed: {' → '.join(workflow_summary.get('operations', []))}")
        print(f"Intermediate results: {workflow_summary.get('intermediate_results')}")
        print(f"Final result: {workflow_summary.get('final_result')}")
    else:
        print("No workflow summary found in shared state")
    
    print(f"\nAll shared state keys: {list(execution.state.keys())}")

    print("\n=== Workflow Serialization Test ===")
    
    # Test serialization
    print("1. Serializing workflow...")
    dumped_config = workflow.dump_component()
    print(f"   Serialized config type: {type(dumped_config)}")
    print(f"   Config provider: {dumped_config.provider}")
    print(f"   Config version: {dumped_config.version}")

    

    # Save workflow to json file for UI integration
    print("4. Saving workflow JSON for UI...")
    with open("simple_sequential_workflow.json", "w") as f:
        f.write(dumped_config.model_dump_json(indent=2))
    print("   ✅ Saved to simple_sequential_workflow.json") 


if __name__ == "__main__":
    asyncio.run(main())
