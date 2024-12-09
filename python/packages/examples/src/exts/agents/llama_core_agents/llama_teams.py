import json
import uuid
from typing import List, Tuple

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import MessageContext, TopicId
from autogen_core.components import FunctionCall, RoutedAgent, TypeSubscription, message_handler
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.components.tools import FunctionTool, Tool
from autogen_ext.models import OpenAIChatCompletionClient
from pydantic import BaseModel
from .llama_index_routed_agent import LlamaIndexRoutedAgent


# Define a tool
async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."

class SwarmGroup:
    def __init__(self) -> None:
        self.runtime = SingleThreadedAgentRuntime()
        self.weather_agent="weather_agent"
    

    async def init(self):
        weather_agent_type = await LlamaIndexRoutedAgent.register(
        self.runtime,
        type=self.weather_agent,  # Using the topic type as the agent type.
        factory=lambda: LlamaIndexRoutedAgent(
            description="A triage agent.",
            system_message="You are a customer service bot for ACME Inc. "
                "Introduce yourself. Always be very brief. "
                "Gather information to direct the customer to the right department. "
                "But make your questions subtle and natural.",
            tools=[get_weather],
            handoffs=["user"],
           
        ),
    )
        # Add subscriptions for the triage agent: it will receive messages published to its own topic only.
        await self.runtime.add_subscription(TypeSubscription(topic_type=self.weather_agent, agent_type=weather_agent_type.type))