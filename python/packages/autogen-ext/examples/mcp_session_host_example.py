"""
Interactive MCP Host Capabilities Demo

This example demonstrates advanced MCP host capabilities including:
- Sampling: Language model text generation requests from MCP server back to host
- Elicitation: Interactive user input collection through command-line
- Roots: File system root listing

The demo is fully interactive and allows you to communicate directly with
the MCP server through the command line interface.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import yaml
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import (
    GroupChatAgentElicitor,
    McpSessionHost,
    McpWorkbench,
    StdioServerParams,
)
from mcp.types import Root
from pydantic import FileUrl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # Clean format for demo output
)
logger = logging.getLogger(__name__)
logging.getLogger("autogen_core").setLevel(logging.WARNING)


def load_model_client_from_config(config_path: str) -> ChatCompletionClient:
    """Load a ChatCompletionClient from a JSON or YAML config file.

    Args:
        config_path: Path to the JSON or YAML config file

    Returns:
        ChatCompletionClient: Loaded model client

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config format is invalid or unsupported file type
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load config based on file extension
    if config_file.suffix.lower() == ".json":
        with open(config_file, "r") as f:
            config_data = json.load(f)
    elif config_file.suffix.lower() in [".yml", ".yaml"]:
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)
    else:
        raise ValueError(f"Unsupported config file type: {config_file.suffix}. Use .json, .yml, or .yaml")

    if not isinstance(config_data, dict):
        raise ValueError("Config file must contain a JSON/YAML object")

    logger.info(f"📄 Loading ChatCompletionClient from config: {config_path}")
    return ChatCompletionClient.load_component(config_data)


async def interactive_mcp_demo(config_path: str | None = None):
    """Interactive MCP host capabilities demo with command-line interface."""
    logger.info("🌟 Interactive MCP Host Capabilities Demo")
    logger.info("=" * 60)
    logger.info("This demo showcases MCP server-to-host communication:")
    logger.info("• Sampling: MCP server requests language model generation")
    logger.info("• Elicitation: MCP server requests user input via AgentElicitor")
    logger.info("• Roots: MCP server lists available file system roots")
    logger.info("=" * 60)

    # Setup model client for sampling
    if config_path:
        logger.info("⚙️ Loading model client from config file...")
        model_client = load_model_client_from_config(config_path)
    else:
        logger.info("⚙️ Setting up default OpenAI model client (gpt-4)...")
        model_client = OpenAIChatCompletionClient(model="gpt-4")

    # Create user proxy for interactive input and elicitation target
    user_proxy = UserProxyAgent("user_proxy")

    other_assistant = AssistantAgent(
        "booking_assistant",
        model_client=model_client,
        description="An AI assistant who helps a user book 5pm reservations.",
    )

    # Start runtime and create AgentElicitor that targets the UserProxy
    logger.info("🎯 Creating GroupChatAgentElicitor...")
    elicitor = GroupChatAgentElicitor("booking_assistant", model_client=model_client)

    # Create host with all capabilities including elicitation
    logger.info("🏠 Creating MCP session host with sampling, elicitation, and roots support...")
    host = McpSessionHost(
        model_client=model_client,  # Support sampling via model clicent
        elicitor=elicitor,  # Support elicitation via booking_assistant
        # support roots in /home and /tmp
        roots=[Root(uri=FileUrl("file:///home"), name="Home"), Root(uri=FileUrl("file:///tmp"), name="Tmp")],
    )

    # Setup workbench with host
    logger.info("🔧 Creating MCP Workbench for mcp_example_server...")
    mcp_workbench = McpWorkbench(
        server_params=StdioServerParams(
            command=sys.executable,
            args=[str(Path(__file__).parent / "mcp_example_server.py")],
            read_timeout_seconds=60,
        ),
        host=host,
    )

    # Create assistant with MCP capabilities
    assistant = AssistantAgent(
        "mcp_assistant",
        model_client=model_client,
        workbench=mcp_workbench,
        description="An AI assistant with access to MCP tools that can request sampling and elicitation from the host",
    )

    # Create RoundRobinGroupChat with the agents
    logger.info("🔄 Setting up RoundRobinGroupChat...")
    team = RoundRobinGroupChat(
        [assistant, other_assistant, user_proxy], termination_condition=MaxMessageTermination(max_messages=2)
    )

    # TODO: How to improve this dev experience? Or make it more automatic somehow...
    elicitor.set_group_chat(team)

    # Run the team with the initial task
    tasks = ["Book a table for 2 at 7pm", "Generate a poem about computer protocols.", "ls /home", "ls /bin"]
    for task in tasks:
        await team.reset()
        result = await Console(team.run_stream(task=task))

        logger.info("💬 Team conversation:")
        for message in result.messages:
            header = f"--- {type(message).__name__.upper()} ---"
            logger.info(header)
            logger.info(message.model_dump_json(indent=2))


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Interactive MCP Host Capabilities Demo with AgentElicitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default OpenAI GPT-4 client
  python mcp_elicitation_example.py

  # Run with custom model client from config
  python mcp_elicitation_example.py --config model_config.json
  python mcp_elicitation_example.py --config model_config.yaml

Config file format (JSON/YAML):
{
  "component_type": "OpenAIChatCompletionClient",
  "model": "gpt-4",
  "api_key": "your-api-key"
}
        """,
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to JSON or YAML config file containing ChatCompletionClient configuration",
    )

    return parser.parse_args()


async def main():
    """
    Run the interactive MCP host capabilities demonstration.

    This demo allows direct command-line interaction with an MCP-enabled assistant
    that can use tools requiring host-side capabilities like sampling and elicitation.
    """
    args = parse_arguments()

    try:
        await interactive_mcp_demo(config_path=args.config)
    except KeyboardInterrupt:
        logger.info("\n👋 Demo interrupted by user. Goodbye!")
    except Exception as e:
        logger.error(f"❌ Error running demo: {e}")
        logger.info("Troubleshooting tips:")
        logger.info("1. Install the everything server:")
        logger.info("   npm install -g @modelcontextprotocol/server-everything")
        logger.info("2. Ensure your OpenAI API key is configured")
        logger.info("3. Check that Node.js and npx are available in your PATH")
        logger.info("4. Make sure you have internet connectivity for npm package download")
        if args.config:
            logger.info("5. Check that your config file exists and contains valid ChatCompletionClient configuration")


if __name__ == "__main__":
    """
    Interactive MCP Host Capabilities Demo with AgentElicitor

    This demo provides a command-line interface to interact with an MCP-enabled
    assistant that demonstrates advanced host capabilities:

    🔄 Sampling: MCP server can request language model text generation from the host
    ❓ Elicitation: MCP server can request interactive user input via AgentElicitor → UserProxy
    📁 Roots: MCP server can request file system root listings from the host

    Key Features:
    - AgentElicitor routes elicitation requests from MCP server to UserProxyAgent
    - Full bidirectional communication between MCP server and AutoGen agents
    - Interactive command-line interface for real-time demonstration

    Prerequisites:
    1. Install the everything reference server:
       npm install -g @modelcontextprotocol/server-everything
    2. Set up your OpenAI API key (required for sampling capability)
    3. Ensure Node.js and npx are available in your PATH

    Usage:
    - Run with default model: python mcp_elicitation_example.py
    - Run with custom model: python mcp_elicitation_example.py --config model.json
    - Interact through the command-line interface
    - Ask the assistant to use MCP tools that demonstrate host capabilities
    - Watch elicitation requests get routed through the AgentElicitor
    - Type 'quit' to exit the interactive session
    """

    # Run the interactive demo
    asyncio.run(main())
