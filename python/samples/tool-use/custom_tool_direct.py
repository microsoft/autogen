"""
This example shows how to use custom function tools with a tool-enabled
agent.
"""

import asyncio
import os
import random
import sys
from typing import List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components.models import (
    SystemMessage,
)
from agnext.components.tool_agent import ToolAgent
from agnext.components.tools import FunctionTool, Tool
from agnext.core import AgentInstantiationContext
from typing_extensions import Annotated

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agnext.core import AgentId
from coding_direct import Message, ToolUseAgent
from common.utils import get_chat_completion_client_from_envs


async def get_stock_price(ticker: str, date: Annotated[str, "The date in YYYY/MM/DD format."]) -> float:
    """Get the stock price of a company."""
    # This is a placeholder function that returns a random number.
    return random.uniform(10, 100)


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()
    tools: List[Tool] = [
        # A tool that gets the stock price.
        FunctionTool(
            get_stock_price,
            description="Get the stock price of a company given the ticker and date.",
            name="get_stock_price",
        )
    ]
    # Register agents.
    await runtime.register(
        "tool_executor_agent",
        lambda: ToolAgent(
            description="Tool Executor Agent",
            tools=tools,
        ),
    )
    await runtime.register(
        "tool_enabled_agent",
        lambda: ToolUseAgent(
            description="Tool Use Agent",
            system_messages=[SystemMessage("You are a helpful AI Assistant. Use your tools to solve problems.")],
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            tool_schema=[tool.schema for tool in tools],
            tool_agent=AgentId("tool_executor_agent", AgentInstantiationContext.current_agent_id().key),
        ),
    )
    tool_use_agent = AgentId("tool_enabled_agent", "default")

    runtime.start()

    # Send a task to the tool user.
    response = await runtime.send_message(Message("What is the stock price of NVDA on 2024/06/01"), tool_use_agent)
    # Print the result.
    assert isinstance(response, Message)
    print(response.content)

    # Run the runtime until the task is completed.
    await runtime.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
