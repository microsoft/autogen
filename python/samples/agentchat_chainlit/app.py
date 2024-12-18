import os
import chainlit as cl
from typing import Optional
from autogen_core import CancellationToken
import asyncio

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.base import TaskResult


async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."


async def chainlit_input_func(prompt: str, cancellation_token: Optional[CancellationToken] = None) -> str:
    try:
        # Create an AskUserMessage to get user input
        response = await cl.AskUserMessage(
            content=prompt,
            author="System",
            timeout=3600,  # 1 hour timeout, adjust as needed
        ).send()

        if response is None:
            raise RuntimeError("No response received from user")
        return response["output"]

    except Exception as e:
        raise RuntimeError(f"Failed to get user input: {str(e)}") from e


@cl.on_chat_start
async def start_chat():
    cl.user_session.set(
        "prompt_history",
        "",
    )


async def run_team(query: str):
    assistant_agent = AssistantAgent(
        name="assistant_agent", tools=[get_weather], model_client=OpenAIChatCompletionClient(model="gpt-4o-2024-08-06")
    )
    user_proxy_agent = UserProxyAgent(
        name="user_proxy_agent",
        input_func=chainlit_input_func,
    )

    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)
    team = RoundRobinGroupChat(participants=[assistant_agent, user_proxy_agent], termination_condition=termination)

    response_stream = team.run_stream(task=query)
    async for msg in response_stream:
        if hasattr(msg, "content"):
            msg = cl.Message(content=msg.content, author="Agent Team")
            await msg.send()
        if isinstance(msg, TaskResult):
            msg = cl.Message(content="Termination condition met.", author="Agent Team")
            await msg.send()


@cl.on_message
async def cha(message: cl.Message):
    await run_team(message.content)
