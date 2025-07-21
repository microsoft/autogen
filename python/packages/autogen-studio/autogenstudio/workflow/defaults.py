"""
Default echo chain workflow for AutoGen Studio.

Provides the echo chain workflow and its steps from the original example.
"""

from typing import List
from autogen_core import ComponentModel
from pydantic import BaseModel, Field

from .core import Workflow, StepMetadata, WorkflowMetadata, EdgeCondition
from .steps import EchoStep, HttpStep, AgentStep, TransformStep
from .steps._http import HttpRequestInput, HttpResponseOutput
from .steps._agent import AgentInput, AgentOutput


class MessageInput(BaseModel):
    message: str


class MessageOutput(BaseModel):
    result: str


class WebpageInput(BaseModel):
    """UI-friendly input for webpage summarization workflow."""
    url: str = Field(
        default="https://httpbin.org/html",
        description="URL of the webpage to summarize",
        examples=["https://example.com", "https://news.ycombinator.com"]
    )
    message: str = Field(
        default="Starting workflow execution",
        description="Optional message (ignored, for UI compatibility)"
    )


class CollectedOutput(BaseModel):
    """Output model for collected results from multiple processing streams."""
    collected_results: list[str] = Field(description="List of processed results from parallel streams")
    total_processed: int = Field(description="Total number of items processed")
    processing_summary: str = Field(description="Summary of the processing workflow")


def _create_echo_steps():
    """Create complex echo chain steps demonstrating parallel processing, validation, and fan-out/fan-in."""
    
    # Step 1: Receive and broadcast message
    receive_step = EchoStep(
        step_id="receive",
        metadata=StepMetadata(
            name="Receive Message",
            description="Initial step to receive and broadcast a message to parallel processing streams", 
            tags=["input", "broadcast"]
        ),
        input_type=MessageInput,
        output_type=MessageOutput,
        prefix="📥 RECEIVED: ",
        suffix=" [BROADCASTING TO PARALLEL STREAMS]",
        delay_seconds=2
    )
    
    # Parallel Processing Steps (Fan-out)
    process_urgent_step = EchoStep(
        step_id="process_urgent",
        metadata=StepMetadata(
            name="Process Urgent", 
            description="Fast processing stream for urgent messages",
            tags=["processing", "urgent", "fast"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="🚨 URGENT: ",
        suffix=" [FAST-TRACKED]",
        delay_seconds=3  # Fast processing
    )
    
    process_standard_step = EchoStep(
        step_id="process_standard",
        metadata=StepMetadata(
            name="Process Standard",
            description="Standard processing stream for regular messages", 
            tags=["processing", "standard", "medium"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="📋 STANDARD: ",
        suffix=" [PROCESSED]",
        delay_seconds=7  # Medium processing
    )
    
    process_detailed_step = EchoStep(
        step_id="process_detailed",
        metadata=StepMetadata(
            name="Process Detailed",
            description="Detailed processing stream for complex analysis",
            tags=["processing", "detailed", "slow"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="🔍 DETAILED: ",
        suffix=" [DEEP-ANALYZED]",
        delay_seconds=12  # Slow, thorough processing
    )
    
    # Validation Steps for each processing stream
    validate_urgent_step = EchoStep(
        step_id="validate_urgent",
        metadata=StepMetadata(
            name="Validate Urgent",
            description="Quick validation for urgent processing results",
            tags=["validation", "urgent"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="✅ URGENT-VALIDATED: ",
        suffix=" [APPROVED-FAST]", 
        delay_seconds=1
    )
    
    validate_standard_step = EchoStep(
        step_id="validate_standard", 
        metadata=StepMetadata(
            name="Validate Standard",
            description="Standard validation for regular processing results",
            tags=["validation", "standard"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="✅ STANDARD-VALIDATED: ",
        suffix=" [APPROVED-NORMAL]",
        delay_seconds=4
    )
    
    validate_detailed_step = EchoStep(
        step_id="validate_detailed",
        metadata=StepMetadata(
            name="Validate Detailed", 
            description="Thorough validation for detailed processing results",
            tags=["validation", "detailed"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="✅ DETAILED-VALIDATED: ",
        suffix=" [APPROVED-THOROUGH]",
        delay_seconds=6
    )
    
    # Collector Step (Fan-in) using TransformStep for serializable aggregation
    collect_step = TransformStep(
        step_id="collect",
        metadata=StepMetadata(
            name="Collect Results",
            description="Collect and aggregate results from all parallel processing streams",
            tags=["collection", "aggregation", "fan-in"]
        ),
        input_type=MessageOutput,  # Will receive from any validation step
        output_type=CollectedOutput,
        mappings={
            "collected_results": ["static:Results from all parallel processing streams"],
            "total_processed": 3,  # Number of parallel streams
            "processing_summary": "result"  # Use the result field from the triggering validation step
        }
    )
    
    # Final Send Step
    send_step = EchoStep(
        step_id="send",
        metadata=StepMetadata(
            name="Send Final Results",
            description="Send aggregated results from all processing streams",
            tags=["output", "final"]
        ),
        input_type=CollectedOutput,
        output_type=MessageOutput,
        prefix="📤 FINAL RESULTS: ",
        suffix=" [DELIVERED TO ALL STAKEHOLDERS]",
        delay_seconds=3
    )
    
    return [
        receive_step,
        process_urgent_step, process_standard_step, process_detailed_step,
        validate_urgent_step, validate_standard_step, validate_detailed_step,
        collect_step, send_step
    ]


def create_echo_chain_workflow() -> ComponentModel:
    """Create a complex echo chain workflow demonstrating parallel processing, validation, and fan-out/fan-in patterns."""
    
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Complex Echo Processing Workflow",
            description="Parallel message processing with urgent/standard/detailed streams, validation, and result aggregation", 
            version="2.0.0",
            tags=["demo", "echo", "parallel", "fan-out", "fan-in", "validation"]
        )
    )
    
    # Get the shared steps
    steps = _create_echo_steps()
    
    # Add steps to workflow
    for step in steps:
        workflow.add_step(step)
    
    # Create complex parallel processing pattern:
    # 
    # receive → [process_urgent, process_standard, process_detailed] (FAN-OUT)
    #              ↓                    ↓                    ↓
    #         validate_urgent    validate_standard    validate_detailed
    #              ↓                    ↓                    ↓
    #              └────────── collect ─────────────┘ (FAN-IN)
    #                             ↓
    #                           send
    
    # Set start step
    workflow.set_start_step("receive")
    
    # Fan-out: receive broadcasts to all three processing streams
    workflow.add_edge("receive", "process_urgent")
    workflow.add_edge("receive", "process_standard") 
    workflow.add_edge("receive", "process_detailed")
    
    # Each processing stream flows to its validation step
    workflow.add_edge("process_urgent", "validate_urgent")
    workflow.add_edge("process_standard", "validate_standard")
    workflow.add_edge("process_detailed", "validate_detailed")
    
    # Fan-in: all validation steps feed into the collector
    workflow.add_edge("validate_urgent", "collect")
    workflow.add_edge("validate_standard", "collect")
    workflow.add_edge("validate_detailed", "collect")
    
    # Final step: collector feeds into send
    workflow.add_edge("collect", "send")
    
    # Set end step
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

    # Transform UI input to HTTP input
    input_transform = TransformStep(
        step_id="input_transform",
        metadata=StepMetadata(
            name="Input Transform",
            description="Transform UI input to HTTP request",
            tags=["transform", "input"]
        ),
        input_type=WebpageInput,
        output_type=HttpRequestInput,
        mappings={
            "url": "url",  # Extract URL from UI input
            "method": "static:GET",
            "timeout": 30,
            "verify_ssl": True,
            "headers": {},  # Empty dict for headers
            "data": {}      # Empty dict for data
        }
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
            "context_data": {"content": "content"}  # Dict with content field mapped to input.content
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

    workflow.add_step(input_transform)
    workflow.add_step(http_step)
    workflow.add_step(transform_step)
    workflow.add_step(agent_step)
    workflow.add_edge("input_transform", "http_fetch")
    workflow.add_edge("http_fetch", "transform_to_agent_input")
    workflow.add_edge("transform_to_agent_input", "agent_summarize")
    workflow.set_start_step("input_transform")  # Start with UI-friendly input
    workflow.add_end_step("agent_summarize")

    return workflow.dump_component()


class ConditionalInput(BaseModel):
    """Input for conditional workflow."""
    message: str = Field(description="Message to process")
    priority: str = Field(
        default="normal",
        description="Priority level: urgent, normal, or low",
        examples=["urgent", "normal", "low"]
    )
    enable_validation: bool = Field(
        default=True,
        description="Whether to enable validation step"
    )


def create_conditional_workflow() -> ComponentModel:
    """Create a simple conditional workflow demonstrating conditional edges."""
    
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Conditional Processing Workflow",
            description="Demonstrates conditional routing based on message priority and validation settings",
            version="1.0.0",
            tags=["demo", "conditional", "routing"]
        )
    )
    
    # Input step for conditional workflow  
    receive_step = EchoStep(
        step_id="receive_conditional",
        metadata=StepMetadata(
            name="Receive Conditional",
            description="Receive message and prepare for conditional routing",
            tags=["input"]
        ),
        input_type=ConditionalInput,  # Proper input schema for UI introspection
        output_type=MessageOutput,
        prefix="📨 CONDITIONAL INPUT: ",
        suffix=" [ROUTING BASED ON CONDITIONS]",
        delay_seconds=1
    )
    
    # Fast track for urgent messages
    urgent_process_step = EchoStep(
        step_id="urgent_process",
        metadata=StepMetadata(
            name="Urgent Process",
            description="Fast processing for urgent messages",
            tags=["processing", "urgent"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="🚨 URGENT FAST-TRACK: ",
        suffix=" [EXPEDITED]",
        delay_seconds=2
    )
    
    # Normal processing
    normal_process_step = EchoStep(
        step_id="normal_process",
        metadata=StepMetadata(
            name="Normal Process",
            description="Standard processing for normal messages",
            tags=["processing", "normal"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="📋 NORMAL PROCESSING: ",
        suffix=" [STANDARD]",
        delay_seconds=5
    )
    
    # Low priority processing
    low_process_step = EchoStep(
        step_id="low_process",
        metadata=StepMetadata(
            name="Low Priority Process",
            description="Slow processing for low priority messages",
            tags=["processing", "low"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="🐌 LOW PRIORITY: ",
        suffix=" [BATCH-PROCESSED]",
        delay_seconds=8
    )
    
    # Optional validation step
    validation_step = EchoStep(
        step_id="validation",
        metadata=StepMetadata(
            name="Validation",
            description="Optional validation step",
            tags=["validation"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="✅ VALIDATED: ",
        suffix=" [APPROVED]",
        delay_seconds=3
    )
    
    # Final delivery
    deliver_step = EchoStep(
        step_id="deliver",
        metadata=StepMetadata(
            name="Deliver",
            description="Final delivery step",
            tags=["output"]
        ),
        input_type=MessageOutput,
        output_type=MessageOutput,
        prefix="📦 DELIVERED: ",
        suffix=" [COMPLETE]",
        delay_seconds=1
    )
    
    # Add steps
    workflow.add_step(receive_step)
    workflow.add_step(urgent_process_step)
    workflow.add_step(normal_process_step)
    workflow.add_step(low_process_step)
    workflow.add_step(validation_step)
    workflow.add_step(deliver_step)
    
    # Set start step
    workflow.set_start_step("receive_conditional")
    
    # Conditional edges based on priority from initial input (state-based)
    urgent_condition = EdgeCondition(
        type="state_based",
        field="priority", 
        operator="==", 
        value="urgent"
    )
    workflow.add_edge(
        "receive_conditional", "urgent_process",
        condition=urgent_condition.model_dump()
    )
    
    normal_condition = EdgeCondition(
        type="state_based",
        field="priority", 
        operator="==", 
        value="normal"
    )
    workflow.add_edge(
        "receive_conditional", "normal_process", 
        condition=normal_condition.model_dump()
    )
    
    low_condition = EdgeCondition(
        type="state_based",
        field="priority", 
        operator="==", 
        value="low"
    )
    workflow.add_edge(
        "receive_conditional", "low_process",
        condition=low_condition.model_dump()
    )
    
    # Conditional validation (only if enable_validation is True)
    validation_enabled_condition = EdgeCondition(
        type="state_based",
        field="enable_validation", 
        operator="==", 
        value=True
    )
    workflow.add_edge(
        "urgent_process", "validation",
        condition=validation_enabled_condition.model_dump()
    )
    workflow.add_edge(
        "normal_process", "validation",
        condition=validation_enabled_condition.model_dump()
    )
    workflow.add_edge(
        "low_process", "validation", 
        condition=validation_enabled_condition.model_dump()
    )
    
    # Skip validation if disabled
    validation_disabled_condition = EdgeCondition(
        type="state_based",
        field="enable_validation", 
        operator="==", 
        value=False
    )
    workflow.add_edge(
        "urgent_process", "deliver",
        condition=validation_disabled_condition.model_dump()
    )
    workflow.add_edge(
        "normal_process", "deliver",
        condition=validation_disabled_condition.model_dump()
    )
    workflow.add_edge(
        "low_process", "deliver",
        condition=validation_disabled_condition.model_dump()
    )
    
    # Validation to delivery
    workflow.add_edge("validation", "deliver")
    
    # Set end step
    workflow.add_end_step("deliver")
    
    return workflow.dump_component()


def get_default_workflows() -> List[ComponentModel]:
    """Get the default workflows."""
    return [
        create_echo_chain_workflow(),
        create_simple_agent_workflow(),
        create_conditional_workflow(),
    ]

  