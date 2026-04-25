import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

async def main():
    # Get the fetch tool from mcp-server-fetch.
    fetch_mcp_server = StdioServerParams(command="uvx", args=["mcp-server-fetch"])
    # Create an MCP workbench which provides a session to the mcp server.
    async with McpWorkbench(fetch_mcp_server) as workbench:
        # Create an agent that can use the fetch tool.
        model_client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
        fetch_agent = AssistantAgent(
            name="fetcher", model_client=model_client, workbench=workbench, reflect_on_tool_use=True
        )
        # Let the agent fetch the content of a URL and summarize it.
        result = await fetch_agent.run(task="Summarize the content of https://en.wikipedia.org/wiki/Seattle")
        assert isinstance(result.messages[-1], TextMessage)
        print(result.messages[-1].content)
        await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
