#!/usr/bin/env python3
"""
Example script demonstrating the DuckDuckGo Search Agent.

This script shows how to:
1. Create a DuckDuckGo search agent
2. Use it to perform web searches
3. Handle the results

Requirements:
- Install required dependencies: pip install httpx beautifulsoup4 html2text
- Set up a model client (OpenAI API key or other compatible model)
"""

import asyncio
import os
import sys
from typing import Optional

# Add the src directory to Python path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from autogen_ext.agents.duckduckgo_search import DuckDuckGoSearchAgent
from autogen_ext.tools.web_search import DuckDuckGoSearchTool


# Mock model client for demonstration (replace with actual model client)
class MockModelClient:
    """Mock model client for demonstration purposes."""
    
    def __init__(self):
        self.model_info = {
            "vision": False,
            "function_calling": True,
            "json_output": False,
            "family": "mock",
            "structured_output": False
        }
    
    async def create(self, messages, **kwargs):
        """Mock create method that simulates a model response."""
        # In a real implementation, this would call the actual model
        return type('MockResult', (), {
            'content': 'Based on my search, I found relevant information about your query.',
            'usage': None
        })()


async def example_search_tool():
    """Example of using the DuckDuckGo search tool directly."""
    print("=== DuckDuckGo Search Tool Example ===")
    
    # Create the search tool
    search_tool = DuckDuckGoSearchTool()
    
    # Import the arguments class
    from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs
    from autogen_core import CancellationToken
    
    # Create search arguments
    search_args = DuckDuckGoSearchArgs(
        query="Python programming tutorial",
        num_results=3,
        include_snippets=True,
        include_content=False,  # Set to False for faster results
    )
    
    try:
        # Perform the search
        print(f"Searching for: {search_args.query}")
        result = await search_tool.run(search_args, CancellationToken())
        
        # Display results
        print(f"\nFound {len(result.results)} results:")
        for i, search_result in enumerate(result.results, 1):
            print(f"\n{i}. {search_result['title']}")
            print(f"   URL: {search_result['link']}")
            if search_result.get('snippet'):
                print(f"   Snippet: {search_result['snippet'][:200]}...")
                
    except Exception as e:
        print(f"Search failed: {e}")


async def example_search_agent():
    """Example of using the DuckDuckGo search agent."""
    print("\n=== DuckDuckGo Search Agent Example ===")
    
    # Create a mock model client (replace with actual model client)
    model_client = MockModelClient()
    
    # Create the DuckDuckGo search agent
    agent = DuckDuckGoSearchAgent(
        name="research_agent",
        model_client=model_client,
        description="A research agent that uses DuckDuckGo for web searches"
    )
    
    print(f"Created agent: {agent.name}")
    print(f"Description: {agent.description}")
    print(f"Number of tools: {len(agent._tools)}")
    print(f"Tool name: {agent._tools[0].name}")


async def example_with_real_model():
    """Example using a real model client (requires API key)."""
    print("\n=== Real Model Client Example ===")
    
    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found. Skipping real model example.")
        print("To use this example, set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    try:
        # Try to import OpenAI model client
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        
        # Create a real model client
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o-mini",  # Use a cost-effective model
            api_key=api_key
        )
        
        # Create the DuckDuckGo search agent
        agent = DuckDuckGoSearchAgent(
            name="research_agent",
            model_client=model_client
        )
        
        print("Created agent with real model client!")
        print("You can now use agent.run() to perform searches with AI assistance.")
        
        # Example of how to use it (commented out to avoid API calls in demo)
        result = await agent.run(task="Find information about Python web frameworks")
        print(result.messages[-1].content)
        
    except ImportError:
        print("OpenAI model client not available. Install with:")
        print("pip install autogen-ext[openai]")
    except Exception as e:
        print(f"Error creating real model client: {e}")


async def main():
    """Main function demonstrating all examples."""
    print("DuckDuckGo Search Agent Examples")
    print("=" * 40)
    
    # Example 1: Direct tool usage
    await example_search_tool()
    
    # Example 2: Agent with mock model
    await example_search_agent()
    
    # Example 3: Agent with real model (if available)
    await example_with_real_model()
    
    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nNext steps:")
    print("1. Install required dependencies: pip install httpx beautifulsoup4 html2text")
    print("2. Set up your model client (OpenAI, Azure, etc.)")
    print("3. Use the DuckDuckGoSearchAgent in your applications")


if __name__ == "__main__":
    asyncio.run(main()) 