import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    # Create an OpenAI model client.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-2024-08-06",
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
        system_message="Provide constructive feedback. Respond with 'APPROVE' to when your feedbacks are addressed.",
    )
    # Define termination conditions.
    text_termination = TextMentionTermination("APPROVE")
    external_termination = ExternalTermination()
    # Combine conditions with bitwise OR.
    team = RoundRobinGroupChat(
        [primary_agent, critic_agent],
        termination_condition=external_termination | text_termination,
    )
    # Run the team in a background task.
    run = asyncio.create_task(Console(team.run_stream(task="Write a short poem about the fall season.")))
    # Wait for a short time, then stop the team externally.
    await asyncio.sleep(0.1)
    external_termination.set()
    await run
    # Reset and resume the team for a follow-up (no new task).
    await team.reset()
    print("\n--- Resuming team for follow-up ---")
    await Console(team.run_stream())
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
