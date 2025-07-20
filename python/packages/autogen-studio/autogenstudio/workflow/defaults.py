"""
Default echo chain workflow for AutoGen Studio.

Provides the echo chain workflow and its steps from the original example.
"""

from typing import List
from autogen_core import ComponentModel
from pydantic import BaseModel

from .core import Workflow, StepMetadata, WorkflowMetadata
from .steps import EchoStep, HttpStep, AgentStep, TransformStep
from .steps._http import HttpRequestInput, HttpResponseOutput
from .steps._agent import AgentInput, AgentOutput


class MessageInput(BaseModel):
    message: str


class MessageOutput(BaseModel):
    result: str


def _create_echo_steps() -> List[EchoStep]:
    """Create the echo chain steps that are reused in both workflow and step library."""
    
    # Step 1: Receive and format message
    receive_step = EchoStep(
        step_id="receive",
        metadata=StepMetadata(name="Receive Message",description="Initial step to receive a message", tags=["input"]),
        input_type=MessageInput,
        output_type=MessageOutput,
        prefix="📥 RECEIVED: ",
        suffix=" [INBOX]",
        delay_seconds=10
    )
    
    # Step 2: Process the message  
    process_step = EchoStep(
        step_id="process",
        metadata=StepMetadata(name="Process Message", description="Step to process the received message", tags=["processing"]),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="⚙️ PROCESSING: ",
        suffix=" [ANALYZED]",
        delay_seconds=10
    )
    
    # Step 3: Validate the message
    validate_step = EchoStep(
        step_id="validate", 
        metadata=StepMetadata(name="Validate Message", description="Step to validate the processed message", tags=["validation"]),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="✅ VALIDATED: ",
        suffix=" [APPROVED]",
        delay_seconds=15
    )
    
    # Step 4: Send final message
    send_step = EchoStep(
        step_id="send",
        metadata=StepMetadata(name="Send Message", description="Final step to send the message", tags=["output"]),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="📤 SENT: ",
        suffix=" [DELIVERED]",
        delay_seconds=15
    )
    
    return [receive_step, process_step, validate_step, send_step]


def create_echo_chain_workflow() -> ComponentModel:
    """Create the default echo chain workflow."""
    
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Echo Chain Workflow",
            description="Chain of echo steps that process and transform a message", 
            version="1.0.0",
            tags=["demo", "echo", "chain"]
        )
    )
    
    # Get the shared steps
    steps = _create_echo_steps()
    
    # Add steps to workflow
    for step in steps:
        workflow.add_step(step)
    
    # Create linear chain: receive -> process -> validate -> send
    workflow.add_edge("receive", "process")
    workflow.add_edge("process", "validate") 
    workflow.add_edge("validate", "send")
    
    # Set start and end
    workflow.set_start_step("receive")
    workflow.add_end_step("send")
    
    return workflow.dump_component()


def get_default_steps() -> List[ComponentModel]:
    """Get the echo chain steps.""" 
    return [step.dump_component() for step in _create_echo_steps()]


def create_simple_agent_workflow() -> ComponentModel:
    """Create the simple agent (webpage summarization) workflow."""
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Webpage Summarization",
            description="Fetch a webpage and summarize its content using AI",
            tags=["web", "summarization", "ai"]
        )
    )

    http_step = HttpStep(
        step_id="http_fetch",
        metadata=StepMetadata(
            name="HTTP Fetch",
            description="Fetch webpage content",
            tags=["http", "fetch"]
        )
    )

    transform_step = TransformStep(
        step_id="transform_to_agent_input",
        metadata=StepMetadata(
            name="Transform to Agent Input",
            description="Transform HTTP response to Agent input",
            tags=["transform"]
        ),
        input_type=HttpResponseOutput,
        output_type=AgentInput,
        mappings={
            "system_message": "static:You are a helpful assistant that summarizes web content. Provide concise, informative summaries.",
            "instruction": "static:Please summarize the following HTML content in 2-3 sentences, focusing on the main topic and key information:",
            "model": "static:gpt-4.1-nano",
            "temperature": 0.3,
            "max_tokens": 512,
            "context_data": {"content": "content"}
        }
    )

    agent_step = AgentStep(
        step_id="agent_summarize",
        metadata=StepMetadata(
            name="Agent Summarize",
            description="Summarize content using AI",
            tags=["ai", "summarize"]
        )
    )

    workflow.add_step(http_step)
    workflow.add_step(transform_step)
    workflow.add_step(agent_step)
    workflow.add_edge("http_fetch", "transform_to_agent_input")
    workflow.add_edge("transform_to_agent_input", "agent_summarize")
    workflow.set_start_step("http_fetch")
    workflow.add_end_step("agent_summarize")

    return workflow.dump_component()


def get_default_workflows() -> List[ComponentModel]:
    """Get the default workflows."""
    return [
        create_echo_chain_workflow(),
        create_simple_agent_workflow(),
    ]

  