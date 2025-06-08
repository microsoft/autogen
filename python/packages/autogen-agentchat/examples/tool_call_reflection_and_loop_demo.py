#!/usr/bin/env python3
"""
Tool Call Reflection and Loop Functionality Demo

This example demonstrates two key features of the AssistantAgent:

1. Tool Reflection Fix: Tools are now properly passed to the reflection flow,
   preventing errors with LLM providers that require tools parameter (like Bedrock via litellm).

2. Tool Call Loop: New functionality that allows agents to make repeated tool calls
   in a loop until the model produces a non-tool response or handoff.

Both features maintain full backward compatibility.
"""

import asyncio
import json
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_core import FunctionCall
from autogen_core.models import CreateResult, RequestUsage
from autogen_ext.models.replay import ReplayChatCompletionClient


def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    return f"The weather in {city} is 73 degrees and Sunny."


def calculate(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        result = eval(expression)  # Note: In production, use a safer evaluation method
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Error calculating {expression}: {str(e)}"


async def demo_issue_6328_fix():
    """Demonstrate fix for issue #6328: Tools parameter passed to reflection flow."""
    print("=== Demo: Issue #6328 Fix - Tools passed to reflection flow ===")
    
    # Create a mock client that simulates the scenario from issue #6328
    model_client = ReplayChatCompletionClient(
        [
            # First call: tool call
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"city": "New York"}), name="get_weather")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            # Second call: reflection (this would fail without the fix)
            CreateResult(
                finish_reason="stop",
                content="Based on the weather data, New York has pleasant weather today with 73 degrees and sunny skies.",
                usage=RequestUsage(prompt_tokens=15, completion_tokens=10),
                cached=False,
            ),
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": "claude-3-5-sonnet",  # Simulate Claude model
            "structured_output": True,
        },
    )
    
    agent = AssistantAgent(
        name="weather_agent",
        model_client=model_client,
        tools=[get_weather],
        system_message="You are a helpful weather assistant.",
        reflect_on_tool_use=True,  # This enables the reflection flow
    )
    
    result = await agent.run(task="What is the weather in New York?")
    
    print(f"✅ Success! Agent completed task with {len(result.messages)} messages")
    print(f"Final response: {result.messages[-1].content}")
    
    # Verify that tools were passed to both calls
    assert len(model_client.create_calls) == 2, "Expected 2 model calls (initial + reflection)"
    
    # Check that both calls received tools parameter
    for i, call in enumerate(model_client.create_calls):
        assert "tools" in call, f"Call {i+1} missing tools parameter"
        assert len(call["tools"]) > 0, f"Call {i+1} has empty tools list"
        print(f"✅ Call {i+1}: tools parameter correctly passed ({len(call['tools'])} tools)")
    
    print()


async def demo_issue_6268_fix():
    """Demonstrate fix for issue #6268: Tool call loop functionality."""
    print("=== Demo: Issue #6268 Fix - Tool call loop functionality ===")
    
    # Create a mock client that simulates multiple tool calls in a loop
    model_client = ReplayChatCompletionClient(
        [
            # First tool call
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"expression": "2 + 2"}), name="calculate")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
            # Second tool call (loop continues)
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="2", arguments=json.dumps({"expression": "4 * 3"}), name="calculate")],
                usage=RequestUsage(prompt_tokens=12, completion_tokens=5),
                cached=False,
            ),
            # Final text response (loop ends)
            CreateResult(
                finish_reason="stop",
                content="I've completed the calculations: 2+2=4 and 4*3=12. Both results are correct!",
                usage=RequestUsage(prompt_tokens=15, completion_tokens=10),
                cached=False,
            ),
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": "gpt-4o",
            "structured_output": True,
        },
    )
    
    agent = AssistantAgent(
        name="calculator_agent",
        model_client=model_client,
        tools=[calculate],
        system_message="You are a helpful calculator assistant.",
        tool_call_loop=True,  # Enable tool call loop
    )
    
    result = await agent.run(task="Calculate 2+2 and then 4*3")
    
    print(f"✅ Success! Agent completed task with {len(result.messages)} messages")
    print(f"Final response: {result.messages[-1].content}")
    
    # Verify that multiple model calls were made due to tool_call_loop
    assert len(model_client.create_calls) == 3, f"Expected 3 model calls, got {len(model_client.create_calls)}"
    print(f"✅ Tool call loop worked: {len(model_client.create_calls)} model calls made")
    
    # Count tool call events
    tool_call_events = [msg for msg in result.messages if hasattr(msg, 'content') and 
                       isinstance(getattr(msg, 'content', None), list) and 
                       len(getattr(msg, 'content', [])) > 0 and
                       isinstance(getattr(msg, 'content', [])[0], FunctionCall)]
    print(f"✅ Tool calls executed: {len(tool_call_events)} tool call events")
    
    print()


async def demo_tool_call_loop_disabled():
    """Demonstrate that tool_call_loop=False works as expected."""
    print("=== Demo: Tool call loop disabled (default behavior) ===")
    
    model_client = ReplayChatCompletionClient(
        [
            # Single tool call
            CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id="1", arguments=json.dumps({"city": "London"}), name="get_weather")],
                usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
                cached=False,
            ),
        ],
        model_info={
            "function_calling": True,
            "vision": True,
            "json_output": True,
            "family": "gpt-4o",
            "structured_output": True,
        },
    )
    
    agent = AssistantAgent(
        name="weather_agent",
        model_client=model_client,
        tools=[get_weather],
        system_message="You are a helpful weather assistant.",
        # tool_call_loop not specified, defaults to False
    )
    
    result = await agent.run(task="What is the weather in London?")
    
    print(f"✅ Success! Agent completed task with {len(result.messages)} messages")
    
    # Should only make one model call since tool_call_loop is disabled
    assert len(model_client.create_calls) == 1, f"Expected 1 model call, got {len(model_client.create_calls)}"
    print(f"✅ Single model call made (tool_call_loop disabled)")
    
    print()


async def main():
    """Run all demonstrations."""
    print("🚀 AutoGen Issue Fixes Demonstration")
    print("=====================================")
    print()
    
    try:
        await demo_issue_6328_fix()
        await demo_issue_6268_fix()
        await demo_tool_call_loop_disabled()
        
        print("🎉 All demonstrations completed successfully!")
        print()
        print("Summary of fixes:")
        print("- Issue #6328: Tools parameter now correctly passed to reflection flow")
        print("- Issue #6268: Tool call loop functionality added with tool_call_loop parameter")
        print("- Both fixes maintain backward compatibility")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
