"""
Webpage summarization workflow example: HTTP fetch → Agent summarize
"""

import asyncio
from pydantic import BaseModel

from autogenstudio.workflow import Workflow, WorkflowRunner, WorkflowMetadata, StepMetadata
from autogenstudio.workflow.steps import HttpStep, AgentStep, TransformStep
from autogenstudio.workflow.steps._http import HttpRequestInput, HttpResponseOutput
from autogenstudio.workflow.steps._agent import AgentInput, AgentOutput
from autogenstudio.workflow.core._models import Context


# Define data models for the workflow
class WebpageInput(BaseModel):
    url: str


class SummaryOutput(BaseModel):
    summary: str
    original_url: str
    model_used: str
    tokens_used: int


# Define step functions for data transformation
async def prepare_http_request(input_data: WebpageInput, context: Context) -> HttpRequestInput:
    """Prepare HTTP request from workflow input."""
    return HttpRequestInput(
        url=input_data.url,
        method="GET",
        timeout=30,
        verify_ssl=True
    )


async def format_final_output(input_data: AgentOutput, context: Context) -> SummaryOutput:
    """Format the final output combining agent response with metadata."""
    # Get original URL from context
    http_request_info = context.get('http_fetch_request_info', {})
    original_url = http_request_info.get('url', 'unknown')
    
    return SummaryOutput(
        summary=input_data.response,
        original_url=original_url,
        model_used=input_data.model_used,
        tokens_used=input_data.tokens_used or 0
    )


async def main():
    """Run the webpage summarization workflow example."""
    
    print("=== Webpage Summarization Workflow Example ===")
    print("Flow: URL → HTTP Fetch → Agent Summarize → Formatted Output")
    print("")
    
    # Create steps
    http_step = HttpStep(
        step_id="http_fetch",
        metadata=StepMetadata(
            name="HTTP Fetch",
            description="Fetch webpage content",
            tags=["http", "fetch"]
        )
    )
    
    # Transformation step to convert HTTP response to Agent input
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
    
    # Create workflow
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Webpage Summarization",
            description="Fetch a webpage and summarize its content using AI",
            tags=["web", "summarization", "ai"]
        )
    )
    
    workflow.add_step(http_step)
    workflow.add_step(transform_step)
    workflow.add_step(agent_step)
    
    # Create sequence
    workflow.add_edge("http_fetch", "transform_to_agent_input")
    workflow.add_edge("transform_to_agent_input", "agent_summarize")
    
    workflow.set_start_step("http_fetch")
    workflow.add_end_step("agent_summarize")

    # --- DUMP AND RELOAD WORKFLOW ---
    print("\n=== Dumping workflow to dict and reloading ===")
    workflow_dump = workflow.dump_component()
    workflow_dump_dict = workflow_dump.model_dump()
    print(f"Workflow dump keys: {list(workflow_dump_dict.keys())}")

    # Try to reload the workflow from the dump
    from autogenstudio.workflow.core._workflow import Workflow as WorkflowClass
    reloaded_workflow = WorkflowClass.load_component(workflow_dump_dict)
    print("Reloaded workflow from dump.")

    # Run workflow with streaming events (original)
    runner = WorkflowRunner()
    initial_input = {"url": "https://httpbin.org/html"}
    print(f"\nRunning ORIGINAL workflow with input: {initial_input}")
    print("\n=== Streaming Events (Original) ===")
    execution = None
    async for event in runner.run_stream(workflow, initial_input):
        print(f"🎯 {event.event_type}: ", end="")
        
        if event.event_type == "workflow_started":
            print(f"Started with input: {event.initial_input}")
            
        elif event.event_type == "step_started":
            print(f"Step '{event.step_id}' started")
            if event.step_id == "http_fetch":
                print(f"    Fetching: {event.input_data.get('url', 'unknown')}")
            elif event.step_id == "transform_to_agent_input":
                print(f"    Transforming HTTP response to Agent input")
            elif event.step_id == "agent_summarize":
                print(f"    Summarizing with {event.input_data.get('model', 'unknown')}")
            
        elif event.event_type == "step_completed":
            print(f"Step '{event.step_id}' completed in {event.duration_seconds:.2f}s")
            if event.step_id == "http_fetch":
                status_code = event.output_data.get('status_code', 'unknown')
                content_length = len(event.output_data.get('content', ''))
                print(f"    Status: {status_code}, Content length: {content_length} chars")
            elif event.step_id == "transform_to_agent_input":
                print(f"    Transformed to Agent input")
            elif event.step_id == "agent_summarize":
                tokens = event.output_data.get('tokens_used', 'unknown')
                cost = event.output_data.get('cost_estimate', 'unknown')
                print(f"    Tokens: {tokens}, Cost: ${cost}")
            
        elif event.event_type == "step_failed":
            print(f"Step '{event.step_id}' failed in {event.duration_seconds:.2f}s: {event.error}")
            
        elif event.event_type == "edge_activated":
            print(f"Edge '{event.from_step}' → '{event.to_step}' activated")
            
        elif event.event_type == "workflow_completed":
            print(f"Workflow completed successfully!")
            execution = event.execution
            
        elif event.event_type == "workflow_failed":
            print(f"Workflow failed: {event.error}")
            execution = event.execution
    
    if execution is None:
        print("❌ No final execution received!")
    else:
        print("\n=== Final Results (Original) ===")
        for step_id, step_exec in execution.step_executions.items():
            print(f"{step_id}: {step_exec.status}")

    # Run workflow with streaming events (reloaded)
    print(f"\nRunning RELOADED workflow with input: {initial_input}")
    print("\n=== Streaming Events (Reloaded) ===")
    execution = None
    async for event in runner.run_stream(reloaded_workflow, initial_input):
        print(f"🎯 {event.event_type}: ", end="")
        
        if event.event_type == "workflow_started":
            print(f"Started with input: {event.initial_input}")
            
        elif event.event_type == "step_started":
            print(f"Step '{event.step_id}' started")
            if event.step_id == "http_fetch":
                print(f"    Fetching: {event.input_data.get('url', 'unknown')}")
            elif event.step_id == "transform_to_agent_input":
                print(f"    Transforming HTTP response to Agent input")
            elif event.step_id == "agent_summarize":
                print(f"    Summarizing with {event.input_data.get('model', 'unknown')}")
            
        elif event.event_type == "step_completed":
            print(f"Step '{event.step_id}' completed in {event.duration_seconds:.2f}s")
            if event.step_id == "http_fetch":
                status_code = event.output_data.get('status_code', 'unknown')
                content_length = len(event.output_data.get('content', ''))
                print(f"    Status: {status_code}, Content length: {content_length} chars")
            elif event.step_id == "transform_to_agent_input":
                print(f"    Transformed to Agent input")
            elif event.step_id == "agent_summarize":
                tokens = event.output_data.get('tokens_used', 'unknown')
                cost = event.output_data.get('cost_estimate', 'unknown')
                print(f"    Tokens: {tokens}, Cost: ${cost}")
            
        elif event.event_type == "step_failed":
            print(f"Step '{event.step_id}' failed in {event.duration_seconds:.2f}s: {event.error}")
            
        elif event.event_type == "edge_activated":
            print(f"Edge '{event.from_step}' → '{event.to_step}' activated")
            
        elif event.event_type == "workflow_completed":
            print(f"Workflow completed successfully!")
            execution = event.execution
            
        elif event.event_type == "workflow_failed":
            print(f"Workflow failed: {event.error}")
            execution = event.execution
    
    if execution is None:
        print("❌ No final execution received (reloaded)!")
    else:
        print("\n=== Final Results (Reloaded) ===")
        for step_id, step_exec in execution.step_executions.items():
            print(f"{step_id}: {step_exec.status}")
    
    # Show shared workflow state
    print("\n=== Shared Workflow State ===")
    state_keys = list(execution.state.keys())
    print(f"State keys: {state_keys}")
    
    # Show request info for debugging
    for step_id in ["http_fetch", "agent_summarize"]:
        request_info = execution.state.get(f'{step_id}_request_info')
        if request_info:
            print(f"\n{step_id} request info:")
            for key, value in request_info.items():
                print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main()) 