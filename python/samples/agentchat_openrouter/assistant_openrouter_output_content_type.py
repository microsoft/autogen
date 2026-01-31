from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelFamily
from autogen_core.tools import FunctionTool
from dotenv import load_dotenv
import os
import asyncio
from pydantic import BaseModel, Field

load_dotenv()

class weather(BaseModel):
    city: str = Field(..., description="The city we get weather from")
    temperature: int = Field(..., description="Temperature in Farenheits")

async def main() -> None:
    # Ensure these are set in your .env file
    model_client = OpenAIChatCompletionClient(
        base_url=os.getenv("OPEN_ROUTER_BASE_URL"),
        api_key=os.getenv("OPEN_ROUTER_API_KEY"),
        model="openai/gpt-oss-20b:free", # Or any OpenRouter model
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": ModelFamily.UNKNOWN,
            "structured_output": True,
        }
    )

    async def get_weather(city: str) -> str:
        """Get the weather for a given city."""
        return f"The weather in {city} is 73 degrees and Sunny."

    agent = AssistantAgent(
        name="weather_agent",
        model_client=model_client,
        tools=[FunctionTool(get_weather, description="get weather", strict=True)],
        output_content_type=weather,
        system_message="You are a helpful assistant. Use your function calls",
        reflect_on_tool_use=True,
        model_client_stream=True,
    )

    await Console(agent.run_stream(task="What is the weather in New York?"))
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
