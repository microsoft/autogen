

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.task import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_agentchat.task import Console

from autogen_core.components.models import UserMessage
from exts.models.litellm.litellm_providers import OpenAiLikeCompletionClient,OllamaChatCompletionClient

import litellm,os
from autogen_core.components.tools import FunctionTool
from autogen_core.components.tools import Tool, ToolSchema,ParametersSchema
from exts.tools.custom_tools_impl import JsonSchemaTool
# 设置可观察性
litellm.success_callback = ["langfuse"]
os.environ['LANGFUSE_SECRET_KEY']="sk-lf-b7935a49-5e9e-4ef7-ba5c-343f1d77456c"
os.environ['LANGFUSE_PUBLIC_KEY']="pk-lf-26e16ca6-57a6-40d8-9d91-930d5b19de48" 
os.environ['LANGFUSE_HOST']="http://127.0.0.1:13001"

def get_ollama_client() -> OllamaChatCompletionClient:
    return OllamaChatCompletionClient(
        model="qwen2.5:14b-instruct-q4_K_M",
         temperature=0.3,max_tokens=100
    )

def get_openaiLike_client() -> OpenAiLikeCompletionClient:
    return OpenAiLikeCompletionClient(
        base_url="http://127.0.0.1:11434/v1",
        api_key="fake",
        model="qwen2.5:14b-instruct-q4_K_M",
         temperature=0.3,max_tokens=100
    )


# Define a tool that gets the weather for a city.
async def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"The weather in {city} is 72 degrees and Sunny."


# Create an assistant agent.
weather_agent = AssistantAgent(
    "assistant",
    model_client=get_openaiLike_client(),
    tools=[get_weather],
    system_message="Respond 'TERMINATE' when task is complete.",
)

# Define a termination condition.
text_termination = TextMentionTermination("TERMINATE")

# Create a single-agent team.
single_agent_team = RoundRobinGroupChat([weather_agent], termination_condition=text_termination)

# Running Team

async def run_team() -> None:
    result = await Console(single_agent_team.run_stream(task="What is the weather in New York?"))
    print(result)

import asyncio
asyncio.run(run_team())