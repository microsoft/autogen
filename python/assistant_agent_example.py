import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Define a tool that searches the web for information.
# For simplicity, we will use a mock function here that returns a static string.
async def web_search(query: str) -> str:
    """Find information on the web"""
    return "AutoGen is a programming framework for building multi-agent applications."

async def main():
    # Create an agent that uses the OpenAI GPT-4o model.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4.1-nano",
        # api_key="YOUR_API_KEY",
    )
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[web_search],
        system_message="Use tools to solve tasks.",
    )
    result = await agent.run(task="Find information on AutoGen")
    print(result.messages)
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
