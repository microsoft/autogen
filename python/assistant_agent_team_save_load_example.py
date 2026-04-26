import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-08-06")
    # Define a team with a single assistant agent
    assistant_agent = AssistantAgent(
        name="assistant_agent",
        system_message="You are a helpful assistant",
        model_client=model_client,
    )
    agent_team = RoundRobinGroupChat([assistant_agent], termination_condition=MaxMessageTermination(max_messages=2))
    # Run the team and stream messages to the console
    print("--- First run: Write a poem ---")
    stream = agent_team.run_stream(task="Write a beautiful poem 3-line about lake tangayika")
    await Console(stream)
    # Save the state of the agent team
    team_state = await agent_team.save_state()
    print("\n--- Reset team and ask about previous poem (should not recall) ---")
    await agent_team.reset()
    stream = agent_team.run_stream(task="What was the last line of the poem you wrote?")
    await Console(stream)
    print("\n--- Load saved state and ask again (should recall) ---")
    await agent_team.load_state(team_state)
    stream = agent_team.run_stream(task="What was the last line of the poem you wrote?")
    await Console(stream)
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
