

# load agentchat
# take a config, create a team of agents, call run to get results.
# stream results to UI.

import logging

from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import CodingAssistantAgent, ToolUseAssistantAgent
from autogen_agentchat.logging import ConsoleLogHandler
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import MaxMessageTermination, RoundRobinGroupChat, SelectorGroupChat
from autogen_core.base import CancellationToken
from autogen_core.components.models import OpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.addHandler(ConsoleLogHandler())
logger.setLevel(logging.INFO)


# Create an OpenAI model client.
model_client = OpenAIChatCompletionClient(
    model="gpt-4o-2024-08-06",
    # api_key="sk-...", # Optional if you have an OPENAI_API_KEY env variable set.
)


class WorkflowManager:
    """ Load agent configuration and run the agents. """

    def __init__(self, config):
        self.config = config  # Configuration object.

        async def get_weather(city: str) -> str:
            return f"The weather in {city} is 72 degrees and Sunny."

        get_weather_tool = FunctionTool(
            get_weather, description="Get the weather for a city")

        tool_use_agent = ToolUseAssistantAgent(
            "tool_use_agent",
            system_message="You are a helpful assistant that solves tasks by only using your tools.",
            model_client=model_client,
            registered_tools=[get_weather_tool],
        )

        self.team = RoundRobinGroupChat([tool_use_agent])

    async def run(self, task: str):
        """ Run the agents on the given task. """
        return self.team.run(task, termination_condition=MaxMessageTermination(10))
