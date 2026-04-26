import asyncio
from autogen_core.tools import FunctionTool
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Define a tool using a Python function.
async def web_search_func(query: str) -> str:
    """Find information on the web"""
    return "AutoGen is a programming framework for building multi-agent applications."

# This step is automatically performed inside the AssistantAgent if the tool is a Python function.
web_search_function_tool = FunctionTool(web_search_func, description="Find information on the web")
print("Tool schema:", web_search_function_tool.schema)

async def main():
    model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[web_search_func],
        system_message="Use tools to solve tasks.",
    )
    await Console(agent.run_stream(task="Find information on AutoGen"))
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
