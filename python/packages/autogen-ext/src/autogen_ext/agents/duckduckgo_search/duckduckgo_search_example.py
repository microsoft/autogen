#!/usr/bin/env python3
"""
Example script demonstrating the DuckDuckGo Search Agent.

This script shows how to:
1. Create a DuckDuckGo search agent
2. Use it to perform web searches
3. Handle the results
4. Advanced usage patterns from the README

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


async def example_search_with_content():
    """Example from README: Using the search tool with content extraction."""
    print("\n=== Search Tool with Content Example (from README) ===")
    
    search_tool = DuckDuckGoSearchTool()
    
    from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs
    from autogen_core import CancellationToken
    
    # Configure search parameters as shown in README
    search_args = DuckDuckGoSearchArgs(
        query="Python machine learning libraries",
        num_results=5,
        include_snippets=True,
        include_content=True,
        content_max_length=5000
    )
    
    try:
        # Perform the search
        result = await search_tool.run(search_args, CancellationToken())
        
        # Process results as shown in README
        for search_result in result.results:
            print(f"Title: {search_result['title']}")
            print(f"URL: {search_result['link']}")
            if search_result.get('snippet'):
                print(f"Snippet: {search_result['snippet']}")
            if search_result.get('content'):
                print(f"Content preview: {search_result['content'][:300]}...")
            print("---")
            
    except Exception as e:
        print(f"Search failed: {e}")


async def example_custom_agent_configuration():
    """Example from README: Custom agent configuration."""
    print("\n=== Custom Agent Configuration Example (from README) ===")
    
    model_client = MockModelClient()
    
    # Create agent with custom settings as shown in README
    agent = DuckDuckGoSearchAgent(
        name="specialized_researcher",
        model_client=model_client,
        description="A specialized research agent for academic papers",
        system_message="""You are an academic research assistant. 
        When searching, focus on scholarly sources and peer-reviewed content.
        Always cite your sources and provide detailed analysis.""",
        num_results=5,
        include_content=True,
        content_max_length=15000
    )
    
    print(f"Created specialized agent: {agent.name}")
    print(f"Description: {agent.description}")
    print(f"System message preview: {agent._system_message[:100]}...")


async def example_multi_language_search():
    """Example from README: Multi-language search."""
    print("\n=== Multi-Language Search Example (from README) ===")
    
    search_tool = DuckDuckGoSearchTool()
    
    from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs
    from autogen_core import CancellationToken
    
    # Search in Spanish as shown in README
    search_args = DuckDuckGoSearchArgs(
        query="inteligencia artificial",
        language="es",
        region="es-es",
        num_results=3
    )
    
    try:
        result = await search_tool.run(search_args, CancellationToken())
        
        print(f"Spanish search results for '{search_args.query}':")
        for i, search_result in enumerate(result.results, 1):
            print(f"{i}. {search_result['title']}")
            print(f"   URL: {search_result['link']}")
            if search_result.get('snippet'):
                print(f"   Snippet: {search_result['snippet'][:150]}...")
            print()
            
    except Exception as e:
        print(f"Multi-language search failed: {e}")


async def example_content_only_search():
    """Example from README: Content-only search for faster results."""
    print("\n=== Content-Only Search Example (from README) ===")
    
    search_tool = DuckDuckGoSearchTool()
    
    from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs
    from autogen_core import CancellationToken
    
    # For faster searches without content extraction
    search_args = DuckDuckGoSearchArgs(
        query="latest tech news",
        include_content=False,
        include_snippets=True,
        num_results=10
    )
    
    try:
        result = await search_tool.run(search_args, CancellationToken())
        
        print(f"Fast search results (snippets only) for '{search_args.query}':")
        for i, search_result in enumerate(result.results, 1):
            print(f"{i}. {search_result['title']}")
            print(f"   URL: {search_result['link']}")
            if search_result.get('snippet'):
                print(f"   Snippet: {search_result['snippet'][:100]}...")
            print()
            
    except Exception as e:
        print(f"Content-only search failed: {e}")


async def example_error_handling():
    """Example from README: Error handling."""
    print("\n=== Error Handling Example (from README) ===")
    
    search_tool = DuckDuckGoSearchTool()
    
    from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs
    from autogen_core import CancellationToken
    
    search_args = DuckDuckGoSearchArgs(
        query="test query",
        num_results=1
    )
    
    try:
        result = await search_tool.run(search_args, CancellationToken())
        if not result.results:
            print("No results found")
        else:
            print(f"Found {len(result.results)} results")
            for search_result in result.results:
                print(f"- {search_result['title']}")
    except Exception as e:
        print(f"Search failed: {e}")


async def example_round_robin_chat():
    """Example demonstrating RoundRobinGroupChat with DuckDuckGo Search Agent."""
    print("\n=== Round Robin Chat with DuckDuckGo Search Agent ===")
    
    # Check if we have OpenAI API key for real implementation
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found. Showing mock implementation.")
        print("To run the real example, set your OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        
        # Mock implementation showing the structure
        model_client = MockModelClient()
        
        researcher = DuckDuckGoSearchAgent(
            name="researcher",
            model_client=model_client,
            description="Researcher that gathers information using DuckDuckGo search",
            system_message="You are a research assistant. Use the DuckDuckGo search tool to find relevant information about the given topic."
        )
        
        print(f"Mock setup complete:")
        print(f"- Created DuckDuckGo researcher: {researcher.name}")
        print(f"- Would create AssistantAgent analyst")
        print(f"- Would create RoundRobinGroupChat with both agents")
        print(f"- Would run collaborative research task")
        return
    
    try:
        # Import required AutoGen components
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import TextMentionTermination
        
        # Create model client
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o-mini",
            api_key=api_key
        )
        
        # Create DuckDuckGo search agent
        researcher = DuckDuckGoSearchAgent(
            name="researcher",
            model_client=model_client,
            description="Researcher that gathers information using DuckDuckGo search",
            system_message="""You are a research assistant. Use the DuckDuckGo search tool to find relevant, 
            up-to-date information about the given topic. Focus on finding credible sources and factual information. 
            After gathering information, summarize your findings clearly."""
        )
        
        # Create analyst agent
        analyst = AssistantAgent(
            name="analyst",
            model_client=model_client,
            description="Analyst that synthesizes and analyzes research findings",
            system_message="""You are a data analyst. Your role is to analyze the research findings provided 
            by the researcher, identify key insights, trends, and implications. Provide a structured analysis 
            with clear conclusions and recommendations. When you're done with your analysis, say TERMINATE."""
        )
        
        # Create round robin group chat
        team = RoundRobinGroupChat(
            participants=[researcher, analyst],
            termination_condition=TextMentionTermination("TERMINATE")
        )
        
        print("Created research team with RoundRobinGroupChat:")
        print(f"- Researcher: {researcher.name}")
        print(f"- Analyst: {analyst.name}")
        print("\nRunning collaborative research task...")
        
        # Run research task
        result = await team.run(
            task="Research the latest developments in artificial intelligence and machine learning in 2024. Focus on breakthrough technologies, major industry trends, and potential impacts on various sectors."
        )
        
        print("\n" + "="*50)
        print("RESEARCH COLLABORATION COMPLETED")
        print("="*50)
        
        # Display the conversation
        for i, message in enumerate(result.messages):
            print(f"\n[Message {i+1}] {message.source}:")
            print(f"{message.content[:500]}{'...' if len(message.content) > 500 else ''}")
        
        print(f"\nTotal messages exchanged: {len(result.messages)}")
        
    except ImportError as e:
        print(f"Required AutoGen components not available: {e}")
        print("Make sure you have the latest autogen-agentchat installed:")
        print("pip install autogen-agentchat")
    except Exception as e:
        print(f"Round robin chat example failed: {e}")


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


async def example_basic_usage_from_readme():
    """Example from README: Basic usage with real model client."""
    print("\n=== Basic Usage Example (from README) ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not found. Showing mock version of README example.")
        print("To run the real example, set your OpenAI API key.")
        
        # Mock version
        model_client = MockModelClient()
        agent = DuckDuckGoSearchAgent(
            name="research_agent",
            model_client=model_client
        )
        print("Created mock agent for demonstration")
        return
    
    try:
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        
        # Create a model client as shown in README
        model_client = OpenAIChatCompletionClient(
            model="gpt-4o-mini",
            api_key=api_key
        )
        
        # Create the DuckDuckGo search agent as shown in README
        agent = DuckDuckGoSearchAgent(
            name="research_agent",
            model_client=model_client
        )
        
        # Use the agent to perform research as shown in README
        result = await agent.run(
            task="Find information about the latest developments in renewable energy"
        )
        
        print("README basic usage example completed!")
        print(f"Result: {result.messages[-1].content}")
        
    except ImportError:
        print("OpenAI model client not available for README example")
    except Exception as e:
        print(f"README example failed: {e}")


async def main():
    """Main function demonstrating all examples."""
    print("DuckDuckGo Search Agent Examples")
    print("=" * 40)
    
    # Basic examples
    await example_search_tool()
    await example_search_agent()
    
    # README examples
    await example_basic_usage_from_readme()
    await example_search_with_content()
    await example_custom_agent_configuration()
    await example_multi_language_search()
    await example_content_only_search()
    await example_error_handling()
    await example_round_robin_chat()
    
    # Real model example
    await example_with_real_model()
    
    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nNext steps:")
    print("1. Install required dependencies: pip install httpx beautifulsoup4 html2text")
    print("2. Set up your model client (OpenAI, Azure, etc.)")
    print("3. Use the DuckDuckGoSearchAgent in your applications")
    print("4. Check the README.md for more detailed documentation")


if __name__ == "__main__":
    asyncio.run(main()) 