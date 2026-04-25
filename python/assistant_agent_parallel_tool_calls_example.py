import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Mock web search tool
def web_search(query: str) -> str:
    return f"Result for: {query}"

async def main():
    # Model client with parallel tool calls disabled
    model_client_no_parallel_tool_call = OpenAIChatCompletionClient(
        model="gpt-4o",
        parallel_tool_calls=False,  # type: ignore
    )
    agent_no_parallel_tool_call = AssistantAgent(
        name="assistant",
        model_client=model_client_no_parallel_tool_call,
        tools=[web_search],
        system_message="Use tools to solve tasks.",
    )
    print("--- Single tool iteration (default) ---")
    await Console(agent_no_parallel_tool_call.run_stream(task="Search for AutoGen and Python"))

    # Agent with multiple tool iterations allowed
    agent_loop = AssistantAgent(
        name="assistant_loop",
        model_client=model_client_no_parallel_tool_call,
        tools=[web_search],
        system_message="Use tools to solve tasks.",
        max_tool_iterations=10,  # At most 10 iterations
    )
    print("--- Multiple tool iterations (max 10) ---")
    await Console(agent_loop.run_stream(task="Search for AutoGen, Python, and AI"))
    await model_client_no_parallel_tool_call.close()

if __name__ == "__main__":
    asyncio.run(main())
