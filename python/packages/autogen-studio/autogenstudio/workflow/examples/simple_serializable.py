"""
Simple Echo Chain Workflow with JSON Serialization

Demonstrates a multi-step workflow using EchoStep and saves results to JSON.
"""

import asyncio
from pydantic import BaseModel
from autogenstudio.workflow.core import Workflow, WorkflowRunner, StepMetadata, WorkflowMetadata
from autogenstudio.workflow.steps import EchoStep


class MessageInput(BaseModel):
    message: str


class MessageOutput(BaseModel):
    result: str


def create_echo_chain_workflow():
    """Create a simple workflow with 4 echo steps that process a message."""
    
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Echo Chain Workflow",
            description="Chain of echo steps that process and transform a message",
            version="1.0.0"
        )
    )
    
    # Step 1: Receive and format message
    receive_step = EchoStep(
        step_id="receive",
        metadata=StepMetadata(name="Receive Message"),
        input_type=MessageInput,
        output_type=MessageOutput,
        prefix="📥 RECEIVED: ",
        suffix=" [INBOX]"
    )
    
    # Step 2: Process the message
    process_step = EchoStep(
        step_id="process",
        metadata=StepMetadata(name="Process Message"),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="⚙️ PROCESSING: ",
        suffix=" [ANALYZED]"
    )
    
    # Step 3: Validate the message
    validate_step = EchoStep(
        step_id="validate",
        metadata=StepMetadata(name="Validate Message"),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="✅ VALIDATED: ",
        suffix=" [APPROVED]"
    )
    
    # Step 4: Send final message
    send_step = EchoStep(
        step_id="send",
        metadata=StepMetadata(name="Send Message"),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="📤 SENT: ",
        suffix=" [DELIVERED]"
    )
    
    # Add steps to workflow
    workflow.add_step(receive_step)
    workflow.add_step(process_step)
    workflow.add_step(validate_step)
    workflow.add_step(send_step)
    
    # Create linear chain: receive -> process -> validate -> send
    workflow.add_edge("receive", "process")
    workflow.add_edge("process", "validate")
    workflow.add_edge("validate", "send")
    
    # Set start and end
    workflow.set_start_step("receive")
    workflow.add_end_step("send")
    
    return workflow


def save_workflow_to_json(workflow, filename="echo_chain_workflow.json"):
    """Save workflow configuration to JSON file using dump_component."""
    
    # Serialize workflow using built-in dump method
    dumped_config = workflow.dump_component()
    
    # Save to JSON file
    with open(filename, 'w') as f:
        f.write(dumped_config.model_dump_json(indent=2))
    
    return dumped_config


async def main():
    """Run the echo chain workflow and save results to JSON."""
    
    print("=== Echo Chain Workflow with JSON Export ===\n")
    
    # Create workflow
    workflow = create_echo_chain_workflow()
    
    # Save workflow configuration to JSON
    print("Saving workflow configuration...")
    config = save_workflow_to_json(workflow, "echo_chain_workflow.json")
    print(f"✅ Workflow saved to echo_chain_workflow.json")
    print(f"Provider: {config.provider}")
    print(f"Version: {config.version}")
    print()
    
    # Test serialization roundtrip
    print("Testing serialization roundtrip...")
    loaded_workflow = Workflow.load_component(config)
    print(f"✅ Workflow loaded successfully!")
    print(f"Loaded workflow name: {loaded_workflow.metadata.name}")
    print(f"Steps in loaded workflow: {list(loaded_workflow.steps.keys())}")
    print()
    
    # Run test with original workflow
    runner = WorkflowRunner()
    input_data = {"message": "Hello Echo Chain!"}
    
    print(f"Running original workflow with: {input_data}")
    execution1 = await runner.run(workflow, input_data)
    
    print("\nMessage transformation (original):")
    for step_id in ["receive", "process", "validate", "send"]:
        if step_id in execution1.step_executions:
            output = execution1.step_executions[step_id].output_data
            if output:
                print(f"  {step_id}: {output['result']}")
    
    # Run test with loaded workflow
    print(f"\nRunning loaded workflow with: {input_data}")
    execution2 = await runner.run(loaded_workflow, input_data)
    
    print("\nMessage transformation (loaded):")
    for step_id in ["receive", "process", "validate", "send"]:
        if step_id in execution2.step_executions:
            output = execution2.step_executions[step_id].output_data
            if output:
                print(f"  {step_id}: {output['result']}")
    
    # Compare results
    final1 = execution1.step_executions['send'].output_data['result']
    final2 = execution2.step_executions['send'].output_data['result']
    
    print(f"\n🔍 Results match: {final1 == final2}")
    print(f"✅ Serialization test complete!")
    


if __name__ == "__main__":
    asyncio.run(main())