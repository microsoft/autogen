import logging

from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import ToolUseAssistantAgent
from autogen_agentchat.logging import ConsoleLogHandler
from autogen_agentchat.task._terminations import MaxMessageTermination
from autogen_agentchat.teams import  RoundRobinGroupChat
from autogen_core.components.tools import FunctionTool
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_agentchat.agents import CodingAssistantAgent
logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.addHandler(ConsoleLogHandler())
logger.setLevel(logging.INFO)


# define a tool
async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."


# wrap the tool for use with the agent
get_weather_tool = FunctionTool(get_weather, description="Get the weather for a city")

def get_model_client() -> OpenAIChatCompletionClient:
    "Mimic OpenAI API using Local LLM Server."
    return OpenAIChatCompletionClient(
        model="gpt-4o",  # Need to use one of the OpenAI models as a placeholder for now.
        api_key="NotRequiredSinceWeAreLocal",
        base_url="http://127.0.0.1:4000",
    )



# define an agent
weather_agent = ToolUseAssistantAgent(
    name="writing_agent",
    model_client=get_model_client(),
    registered_tools=[get_weather_tool],
)

async def runAgent():
    # add the agent to a team
    agent_team = RoundRobinGroupChat([weather_agent])
    # Note: if running in a Python file directly you'll need to use asyncio.run(agent_team.run(...)) instead of await agent_team.run(...)
    return await agent_team.run(
        task="What is the weather in New York?",
        termination_condition=MaxMessageTermination(max_messages=1),
    )
    
    

if __name__=='__main__':
    import asyncio
    result = asyncio.run(runAgent())
    print("\n", result)
