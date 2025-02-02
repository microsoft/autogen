import argparse
import asyncio
import logging
from typing import Any, Dict

import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.models import ChatCompletionClient
from autogen_ext.tools.graphrag import (
    GlobalSearchTool,
    LocalSearchTool,
)


async def main(model_config: Dict[str, Any]) -> None:
    # Initialize the model client from config
    model_client = ChatCompletionClient.load_component(model_config)

    # Set up global search tool
    global_tool = GlobalSearchTool.from_settings(settings_path="./settings.yaml")

    local_tool = LocalSearchTool.from_settings(settings_path="./settings.yaml")

    # Create assistant agent with both search tools
    assistant_agent = AssistantAgent(
        name="search_assistant",
        tools=[global_tool, local_tool],
        model_client=model_client,
        system_message=(
            "You are a tool selector AI assistant using the GraphRAG framework. "
            "Your primary task is to determine the appropriate search tool to call based on the user's query. "
            "For specific, detailed information about particular entities or relationships, call the 'local_search' function. "
            "For broader, abstract questions requiring a comprehensive understanding of the dataset, call the 'global_search' function. "
            "Do not attempt to answer the query directly; focus solely on selecting and calling the correct function."
        ),
    )

    # Run a sample query
    query = "What does the station-master says about Dr. Becher?"
    print(f"\nQuery: {query}")

    await Console(assistant_agent.run_stream(task=query))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a GraphRAG search with an agent.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument(
        "--model-config", type=str, help="Path to the model configuration file.", default="model_config.yaml"
    )
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("autogen_core").setLevel(logging.DEBUG)
        handler = logging.FileHandler("graphrag_search.log")
        logging.getLogger("autogen_core").addHandler(handler)

    with open(args.model_config, "r") as f:
        model_config = yaml.safe_load(f)
    asyncio.run(main(model_config))
