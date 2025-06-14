"""
Example demonstrating OpenAIAgent with built-in tool support.

This example shows how to use the OpenAIAgent with various built-in tools
like file_search, code_interpreter, web_search_preview, etc.
"""

import asyncio
import os
from autogen_core import CancellationToken
from autogen_ext.agents.openai import OpenAIAgent
from autogen_agentchat.messages import TextMessage
from openai import AsyncOpenAI


async def example_with_web_search():
    """Example using web search tool."""
    print("=== Example: OpenAI Agent with Web Search ===")
    
    # Initialize the OpenAI client
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create an agent with web search capability
    agent = OpenAIAgent(
        name="Web Search Agent",
        description="An agent that can search the web for information",
        client=client,
        model="gpt-4.1",
        instructions="You are a helpful assistant that can search the web for current information.",
        tools=["web_search_preview"]
    )
    
    # Create a message asking for current information
    message = TextMessage(
        source="user", 
        content="What are the latest developments in AI technology this week?"
    )
    
    # Get response from the agent
    cancellation_token = CancellationToken()
    try:
        response = await agent.on_messages([message], cancellation_token)
        print(f"Agent response: {response.chat_message.content}")
    except Exception as e:
        print(f"Error: {e}")


async def example_with_code_interpreter():
    """Example using code interpreter tool."""
    print("\n=== Example: OpenAI Agent with Code Interpreter ===")
    
    # Initialize the OpenAI client
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create an agent with code interpreter capability
    agent = OpenAIAgent(
        name="Code Interpreter Agent",
        description="An agent that can execute Python code",
        client=client,
        model="gpt-4.1",
        instructions="You are a helpful assistant that can write and execute Python code to solve problems.",
        tools=["code_interpreter"]
    )
    
    # Create a message asking for a calculation
    message = TextMessage(
        source="user", 
        content="Calculate the first 10 Fibonacci numbers and plot them."
    )
    
    # Get response from the agent
    cancellation_token = CancellationToken()
    try:
        response = await agent.on_messages([message], cancellation_token)
        print(f"Agent response: {response.chat_message.content}")
    except Exception as e:
        print(f"Error: {e}")


async def example_with_multiple_tools():
    """Example using multiple built-in tools."""
    print("\n=== Example: OpenAI Agent with Multiple Tools ===")
    
    # Initialize the OpenAI client
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create an agent with multiple tools
    agent = OpenAIAgent(
        name="Multi-Tool Agent",
        description="An agent with multiple capabilities",
        client=client,
        model="gpt-4.1",
        instructions="You are a versatile assistant with web search, code execution, and file search capabilities.",
        tools=["web_search_preview", "code_interpreter", "file_search"]
    )
    
    # Create a message that might benefit from multiple tools
    message = TextMessage(
        source="user", 
        content="Research the current stock price of Apple and create a simple visualization of its trend."
    )
    
    # Get response from the agent
    cancellation_token = CancellationToken()
    try:
        response = await agent.on_messages([message], cancellation_token)
        print(f"Agent response: {response.chat_message.content}")
    except Exception as e:
        print(f"Error: {e}")


async def example_with_mixed_tools():
    """Example mixing built-in tools with custom function tools."""
    print("\n=== Example: OpenAI Agent with Mixed Tools ===")
    
    from autogen_core.tools import Tool, ToolSchema
    from typing import Any, Mapping, Type
    from pydantic import BaseModel
    
    class CalculatorArgs(BaseModel):
        expression: str
    
    class CalculatorTool(Tool):
        """A simple calculator tool."""
        
        @property
        def name(self) -> str:
            return "calculator"
        
        @property
        def description(self) -> str:
            return "Evaluate mathematical expressions"
        
        @property
        def schema(self) -> ToolSchema:
            return ToolSchema(
                name="calculator",
                description="Evaluate mathematical expressions",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            )
        
        def args_type(self) -> Type[BaseModel]:
            return CalculatorArgs
        
        def return_type(self) -> Type[Any]:
            return float
        
        def state_type(self) -> Type[BaseModel] | None:
            return None
        
        def return_value_as_string(self, value: Any) -> str:
            return str(value)
        
        async def run_json(self, args: Mapping[str, Any], cancellation_token: CancellationToken) -> float:
            expression = args["expression"]
            try:
                # Simple evaluation (in real use, you'd want safer evaluation)
                result = eval(expression)
                return float(result)
            except Exception as e:
                raise ValueError(f"Invalid expression: {e}")
        
        async def load_state_json(self, state: Mapping[str, Any]) -> None:
            pass
        
        async def save_state_json(self) -> Mapping[str, Any]:
            return {}
    
    # Initialize the OpenAI client
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create custom tool
    calculator = CalculatorTool()
    
    # Create an agent with both built-in and custom tools
    agent = OpenAIAgent(
        name="Mixed Tools Agent",
        description="An agent with both built-in and custom tools",
        client=client,
        model="gpt-4.1",
        instructions="You are a helpful assistant with web search and custom calculator capabilities.",
        tools=["web_search_preview", calculator]
    )
    
    # Create a message that uses both types of tools
    message = TextMessage(
        source="user", 
        content="Search for the current price of Bitcoin and calculate what 0.5 BTC would be worth."
    )
    
    # Get response from the agent
    cancellation_token = CancellationToken()
    try:
        response = await agent.on_messages([message], cancellation_token)
        print(f"Agent response: {response.chat_message.content}")
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run all examples."""
    # Check if API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set the OPENAI_API_KEY environment variable to run these examples.")
        print("\nExample tool configurations that would be created:")
        print("- Web Search: {'type': 'web_search_preview'}")
        print("- Code Interpreter: {'type': 'code_interpreter'}")
        print("- File Search: {'type': 'file_search'}")
        print("- Computer Use: {'type': 'computer_use_preview'}")
        print("- Image Generation: {'type': 'image_generation'}")
        print("- MCP: {'type': 'mcp'}")
        return
    
    # Run examples
    await example_with_web_search()
    await example_with_code_interpreter()
    await example_with_multiple_tools()
    await example_with_mixed_tools()


if __name__ == "__main__":
    asyncio.run(main())
