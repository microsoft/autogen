import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        temperature=1,
    )
    # Create the primary agent.
    primary_agent = AssistantAgent(
        "primary",
        model_client=model_client,
        system_message="You are a helpful AI assistant.",
    )
    # Create the critic agent.
    critic_agent = AssistantAgent(
        "critic",
        model_client=model_client,
        system_message="Provide constructive feedback for every message. Respond with 'APPROVE' to when your feedbacks are addressed.",
    )
    # MaxMessageTermination: stops after 3 messages.
    max_msg_termination = MaxMessageTermination(max_messages=3)
    round_robin_team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=max_msg_termination)
    # First run: start the conversation.
    await Console(round_robin_team.run_stream(task="Write a unique, Haiku about the weather in Paris"))
    # Continue the conversation (no new task).
    await Console(round_robin_team.run_stream())
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
