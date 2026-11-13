"""
Sylex Search MCP Example

This example shows how to connect AutoGen agents to the Sylex Search MCP server,
a curated catalog of 11,000+ developer tools and products. The server runs remotely
over SSE — no installation required.

The agent can:
- Search for tools by query (`search.discover`)
- Get detailed info on a specific product (`search.details`)
- Compare multiple products side-by-side (`search.compare`)
- Browse by category (`search.categories`)
- Find alternatives to a known tool (`search.alternatives`)

Prerequisites:
    pip install -U "autogen-agentchat" "autogen-ext[mcp,openai]"

Usage:
    Set OPENAI_API_KEY in your environment, then run:

        python mcp_sylex_search_example.py

    To use a different model provider, replace OpenAIChatCompletionClient with
    any other ChatCompletionClient implementation (Azure, Anthropic, etc.).
"""

import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools

# Sylex Search MCP server — public, no auth required
SYLEX_SEARCH_SSE_URL = "https://mcp-server-production-38c9.up.railway.app/sse"


async def main() -> None:
    # Connect to the Sylex Search MCP server and load all tools.
    # mcp_server_tools() fetches the tool list once and returns an adapter
    # per tool; the adapters handle session management internally.
    server_params = SseServerParams(url=SYLEX_SEARCH_SSE_URL)
    tools = await mcp_server_tools(server_params)

    print(f"Loaded {len(tools)} tools from Sylex Search:")
    for tool in tools:
        print(f"  - {tool.name}")
    print()

    # Build an AssistantAgent that can use all Sylex Search tools.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
    )

    agent = AssistantAgent(
        name="tool_researcher",
        model_client=model_client,
        tools=tools,  # type: ignore[arg-type]
        system_message=(
            "You are a developer tool researcher. "
            "Use the Sylex Search tools to find, compare, and evaluate software products. "
            "Always base your recommendations on the search results — do not guess. "
            "Be concise and structured in your answers."
        ),
    )

    # --- Example 1: discover vector database options ---
    print("=" * 60)
    print("Task 1: Find vector database options")
    print("=" * 60)
    await Console(
        agent.run_stream(
            task="Find the top vector database tools suitable for a Python project with less than 1 GB of data.",
            cancellation_token=CancellationToken(),
        )
    )

    # Reset agent memory between tasks so context doesn't bleed.
    await agent.reset()

    # --- Example 2: compare two specific tools ---
    print()
    print("=" * 60)
    print("Task 2: Compare Pinecone and Weaviate")
    print("=" * 60)
    await Console(
        agent.run_stream(
            task=(
                "Compare Pinecone and Weaviate as vector databases. "
                "Highlight differences in hosting model, pricing tier, and language support."
            ),
            cancellation_token=CancellationToken(),
        )
    )

    # Reset agent memory between tasks.
    await agent.reset()

    # --- Example 3: find alternatives ---
    print()
    print("=" * 60)
    print("Task 3: Find open-source alternatives to Datadog")
    print("=" * 60)
    await Console(
        agent.run_stream(
            task="Find open-source alternatives to Datadog for application monitoring.",
            cancellation_token=CancellationToken(),
        )
    )

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
