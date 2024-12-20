import chainlit as cl
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.base import TaskResult


async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."


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

    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)
    team = RoundRobinGroupChat(participants=[assistant_agent], termination_condition=termination)

    response_stream = team.run_stream(task=query)
    async for msg in response_stream:
        if hasattr(msg, "content"):
            msg = cl.Message(content=msg.content, author="Agent Team")
            await msg.send()
        if isinstance(msg, TaskResult):
            msg = cl.Message(content="Termination condition met. Team and Agents are reset.", author="Agent Team")
            await msg.send()


@cl.on_message
async def chat(message: cl.Message):
    await run_team(message.content)
