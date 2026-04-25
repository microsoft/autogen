import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import TextMentionTermination
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
    # Define a termination condition that stops the task if the critic approves.
    text_termination = TextMentionTermination("APPROVE")
    # Create a team with the primary and critic agents.
    team = RoundRobinGroupChat([primary_agent, critic_agent], termination_condition=text_termination)
    # Reset the team for a new task.
    await team.reset()
    print("--- Streaming team messages ---")
    async for message in team.run_stream(task="Write a short poem about the fall season."):
        if isinstance(message, TaskResult):
            print("Stop Reason:", message.stop_reason)
        else:
            print(message)
    # Or, stream to the console with formatting:
    await team.reset()
    print("\n--- Streaming to Console ---")
    await Console(team.run_stream(task="Write a short poem about the fall season."))
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
