"""Example: Using CRW web scraping tools with AutoGen agents.

Prerequisites:
    1. Install dependencies:
        pip install "autogen-agentchat" "autogen-ext[crw,openai]"

    2. Start a CRW server (https://github.com/nicholasgasior/crw):
        crw --port 3000

    3. Set your OpenAI API key:
        export OPENAI_API_KEY=sk-...

Usage:
    python app.py
"""

import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.crw import CrwCrawlTool, CrwMapTool, CrwScrapeTool

CRW_BASE_URL = "http://localhost:3000"


async def example_scrape() -> None:
    """Scrape a single page and summarize it."""
    print("\n=== Scrape Example ===\n")

    scrape_tool = CrwScrapeTool(base_url=CRW_BASE_URL)
    model = OpenAIChatCompletionClient(model="gpt-4o")
    agent = AssistantAgent(
        "web_scraper",
        model_client=model,
        tools=[scrape_tool],
        system_message="You are a helpful assistant that can scrape web pages and summarize their content.",
    )

    result = await agent.on_messages(
        [TextMessage(content="Scrape https://example.com and give me a brief summary.", source="user")],
        CancellationToken(),
    )
    print(result.chat_message.content)


async def example_map() -> None:
    """Discover all links on a site."""
    print("\n=== Map Example ===\n")

    map_tool = CrwMapTool(base_url=CRW_BASE_URL)
    cancel = CancellationToken()

    result = await map_tool.run_json({"url": "https://example.com"}, cancel)
    print(f"Discovered {len(result.links)} links:")
    for link in result.links[:10]:
        print(f"  - {link}")


async def example_crawl() -> None:
    """Crawl a site and summarize the pages found."""
    print("\n=== Crawl Example ===\n")

    crawl_tool = CrwCrawlTool(base_url=CRW_BASE_URL)
    cancel = CancellationToken()

    result = await crawl_tool.run_json(
        {"url": "https://example.com", "max_depth": 1, "max_pages": 3},
        cancel,
    )
    print(f"Crawled {result.completed}/{result.total} pages (status: {result.status})")
    for page in result.pages:
        print(f"  - {page.source_url}: {page.title}")


async def example_agent_with_all_tools() -> None:
    """Give an agent all three CRW tools for flexible web research."""
    print("\n=== Multi-Tool Agent Example ===\n")

    scrape_tool = CrwScrapeTool(base_url=CRW_BASE_URL)
    crawl_tool = CrwCrawlTool(base_url=CRW_BASE_URL)
    map_tool = CrwMapTool(base_url=CRW_BASE_URL)

    model = OpenAIChatCompletionClient(model="gpt-4o")
    agent = AssistantAgent(
        "web_researcher",
        model_client=model,
        tools=[scrape_tool, crawl_tool, map_tool],
        system_message=(
            "You are a web research assistant. You have three tools:\n"
            "- scrape_url: Scrape a single page and get its content\n"
            "- crawl_website: Crawl multiple pages starting from a URL\n"
            "- map_site: Discover all links on a website\n"
            "Use the most appropriate tool for each request."
        ),
    )

    result = await agent.on_messages(
        [TextMessage(content="Find all the links on https://example.com", source="user")],
        CancellationToken(),
    )
    print(result.chat_message.content)


async def main() -> None:
    await example_scrape()
    await example_map()
    await example_crawl()
    await example_agent_with_all_tools()


if __name__ == "__main__":
    asyncio.run(main())
