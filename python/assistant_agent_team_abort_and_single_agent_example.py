import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import TextMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def abort_team_example():
    # Create an OpenAI model client.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        parallel_tool_calls=False,  # type: ignore
    )
    # Create a tool for incrementing a number.
    def increment_number(number: int) -> int:
        """Increment a number by 1."""
        return number + 1
    # Create a tool agent that uses the increment_number function.
    looped_assistant = AssistantAgent(
        "looped_assistant",
        model_client=model_client,
        tools=[increment_number],
        system_message="You are a helpful AI assistant, use the tool to increment the number.",
    )
    # Termination condition that stops the task if the agent responds with a text message.
    termination_condition = TextMessageTermination("looped_assistant")
    # Create a team with the looped assistant agent and the termination condition.
    team = RoundRobinGroupChat(
        [looped_assistant],
        termination_condition=termination_condition,
    )
    # Create a cancellation token.
    cancellation_token = CancellationToken()
    # Use another coroutine to run the team.
    run = asyncio.create_task(
        team.run(
            task="Increment the number 5 to 10.",
            cancellation_token=cancellation_token,
        )
    )
    # Cancel the run after a short delay.
    await asyncio.sleep(0.1)
    cancellation_token.cancel()
    try:
        result = await run  # This will raise a CancelledError.
    except asyncio.CancelledError:
        print("Task was cancelled.")
    await model_client.close()

async def single_agent_team_example():
    # Create an OpenAI model client.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
        parallel_tool_calls=False,  # type: ignore
    )
    def increment_number(number: int) -> int:
        return number + 1
    looped_assistant = AssistantAgent(
        "looped_assistant",
        model_client=model_client,
        tools=[increment_number],
        system_message="You are a helpful AI assistant, use the tool to increment the number.",
    )
    termination_condition = TextMessageTermination("looped_assistant")
    team = RoundRobinGroupChat(
        [looped_assistant],
        termination_condition=termination_condition,
    )
    async for message in team.run_stream(task="Increment the number 5 to 10."):
        print(type(message).__name__, message)
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(abort_team_example())
    asyncio.run(single_agent_team_example())
