import asyncio
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-08-06")
    assistant_agent = AssistantAgent(
        name="assistant_agent",
        system_message="You are a helpful assistant",
        model_client=model_client,
    )
    agent_team = RoundRobinGroupChat([assistant_agent], termination_condition=MaxMessageTermination(max_messages=2))
    # Run the team and save state
    stream = agent_team.run_stream(task="Write a beautiful poem 3-line about lake tangayika")
    await Console(stream)
    team_state = await agent_team.save_state()
    # Persist state to disk
    with open("/workspaces/autogen/coding/team_state.json", "w") as f:
        json.dump(team_state, f)
    # Simulate loading state in a new team
    with open("/workspaces/autogen/coding/team_state.json", "r") as f:
        loaded_state = json.load(f)
    new_agent_team = RoundRobinGroupChat([assistant_agent], termination_condition=MaxMessageTermination(max_messages=2))
    await new_agent_team.load_state(loaded_state)
    stream = new_agent_team.run_stream(task="What was the last line of the poem you wrote?")
    await Console(stream)
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
