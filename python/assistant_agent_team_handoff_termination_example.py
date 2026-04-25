import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff
from autogen_agentchat.conditions import HandoffTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    # Create an OpenAI model client.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o",
    )
    # Create a lazy assistant agent that always hands off to the user.
    lazy_agent = AssistantAgent(
        "lazy_assistant",
        model_client=model_client,
        handoffs=[Handoff(target="user", message="Transfer to user.")],
        system_message="If you cannot complete the task, transfer to user. Otherwise, when finished, respond with 'TERMINATE'.",
    )
    # Define a termination condition that checks for handoff messages.
    handoff_termination = HandoffTermination(target="user")
    # Define a termination condition that checks for a specific text mention.
    text_termination = TextMentionTermination("TERMINATE")
    # Create a single-agent team with the lazy assistant and both termination conditions.
    lazy_agent_team = RoundRobinGroupChat([lazy_agent], termination_condition=handoff_termination | text_termination)
    # Run the team and stream to the console.
    task = "What is the weather in New York?"
    await Console(lazy_agent_team.run_stream(task=task), output_stats=True)
    # Continue the team by providing the information the agent needs.
    await Console(lazy_agent_team.run_stream(task="The weather in New York is sunny."))
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
