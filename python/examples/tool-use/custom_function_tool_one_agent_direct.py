import asyncio
import os
import random
import sys

from agnext.application import SingleThreadedAgentRuntime
from agnext.components.models import (
    OpenAI,
    SystemMessage,
)
from agnext.components.tools import FunctionTool
from typing_extensions import Annotated

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from coding_one_agent_direct import AIResponse, ToolEnabledAgent, UserRequest


async def get_stock_price(ticker: str, date: Annotated[str, "The date in YYYY/MM/DD format."]) -> float:
    """Get the stock price of a company."""
    # This is a placeholder function that returns a random number.
    return random.uniform(10, 100)


async def main() -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()
    # Register agents.
    tool_agent = runtime.register_and_get(
        "tool_enabled_agent",
        lambda: ToolEnabledAgent(
            description="Tool Use Agent",
            system_messages=[SystemMessage("You are a helpful AI Assistant. Use your tools to solve problems.")],
            model_client=OpenAI(model="gpt-3.5-turbo"),
            tools=[
                # Define a tool that gets the stock price.
                FunctionTool(
                    get_stock_price,
                    description="Get the stock price of a company given the ticker and date.",
                    name="get_stock_price",
                )
            ],
        ),
    )

    # Send a task to the tool user.
    result = runtime.send_message(UserRequest("What is the stock price of NVDA on 2024/06/01"), tool_agent)

    # Run the runtime until the task is completed.
    while not result.done():
        await runtime.process_next()

    # Print the result.
    ai_response = result.result()
    assert isinstance(ai_response, AIResponse)
    print(ai_response.content)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
