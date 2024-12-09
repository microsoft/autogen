from typing import Any, Dict, List

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import HandoffMessage
from autogen_agentchat.task import Console, HandoffTermination, TextMentionTermination
from autogen_agentchat.teams import Swarm
from autogen_ext.models import OpenAIChatCompletionClient
from exts.models.litellm.litellm_providers import OpenAiLikeCompletionClient,OllamaChatCompletionClient

def get_openaiLike_client() -> OpenAiLikeCompletionClient:
    return OpenAiLikeCompletionClient(
        base_url="http://127.0.0.1:11434/v1",
        api_key="fake",
        model="qwen2.5:14b-instruct-q4_K_M",
         temperature=0.3,max_tokens=100
    )

def refund_flight(flight_id: str) -> str:
    """Refund a flight"""
    return f"Flight {flight_id} refunded"
model_client = get_openaiLike_client()

travel_agent = AssistantAgent(
    "travel_agent",
    model_client=model_client,
    handoffs=["flights_refunder", "user"],
    system_message="""You are a travel agent.
    The flights_refunder is in charge of refunding flights.
    If you need information from the user, you must first send your message, then you can handoff to the user.
    Use TERMINATE when the travel planning is complete.""",
)

flights_refunder = AssistantAgent(
    "flights_refunder",
    model_client=model_client,
    handoffs=["travel_agent", "user"],
    tools=[refund_flight],
    system_message="""You are an agent specialized in refunding flights.
    You only need flight reference numbers to refund a flight.
    You have the ability to refund a flight using the refund_flight tool.
    If you need information from the user, you must first send your message, then you can handoff to the user.
    When the transaction is complete, handoff to the travel agent to finalize.""",
)

termination = HandoffTermination(target="user") | TextMentionTermination("TERMINATE")
team = Swarm([travel_agent, flights_refunder], termination_condition=termination)


task = "I need to refund my flight."


async def run_team_stream() -> None:
    task_result = await Console(team.run_stream(task=task))
    last_message = task_result.messages[-1]

    while isinstance(last_message, HandoffMessage) and last_message.target == "user":
        user_message = input("User: ")

        task_result = await Console(
            team.run_stream(task=HandoffMessage(source="user", target=last_message.source, content=user_message))
        )
        last_message = task_result.messages[-1]


import asyncio
import litellm,os
# 设置可观察性
litellm.success_callback = ["langfuse"]
os.environ['LANGFUSE_SECRET_KEY']="sk-lf-b7935a49-5e9e-4ef7-ba5c-343f1d77456c"
os.environ['LANGFUSE_PUBLIC_KEY']="pk-lf-26e16ca6-57a6-40d8-9d91-930d5b19de48" 
os.environ['LANGFUSE_HOST']="http://127.0.0.1:13001"
asyncio.run(run_team_stream())