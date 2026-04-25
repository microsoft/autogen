import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    # Create the agents.
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    assistant = AssistantAgent("assistant", model_client=model_client)
    # Create the team setting a maximum number of turns to 1.
    team = RoundRobinGroupChat([assistant], max_turns=1)
    task = "Write a 4-line poem about the ocean."
    while True:
        # Run the conversation and stream to the console.
        stream = team.run_stream(task=task)
        await Console(stream)
        # Get the user response.
        task = input("Enter your feedback (type 'exit' to leave): ")
        if task.lower().strip() == "exit":
            break
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
