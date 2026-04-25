import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Mock web search tool
def web_search(query: str) -> str:
    return "AutoGen is a programming framework for building multi-agent applications."

async def assistant_run_stream() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[web_search],
        system_message="Use tools to solve tasks.",
    )
    await Console(
        agent.run_stream(task="Find information on AutoGen"),
        output_stats=True,  # Enable stats printing.
    )
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(assistant_run_stream())
