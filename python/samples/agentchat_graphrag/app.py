import asyncio
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.tools.graphrag import (
    GlobalSearchTool,
    LocalSearchTool,
)
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat


async def main():
    # Initialize the OpenAI client
    openai_client = AzureOpenAIChatCompletionClient(
        model="gpt-4o-mini",
        azure_endpoint="https://<resource-name>.openai.azure.com",
        azure_deployment="gpt-4o-mini", 
        api_version="2024-08-01-preview",
        azure_ad_token_provider=get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    )

    # Set up global search tool
    global_tool = GlobalSearchTool.from_settings(
        settings_path="./settings.yaml"
    )


    local_tool = LocalSearchTool.from_settings(
        settings_path="./settings.yaml"
    )

    # Create assistant agent with both search tools
    assistant_agent = AssistantAgent(
        name="search_assistant",
        tools=[global_tool, local_tool],
        model_client=openai_client,
        system_message=(
            "You are a tool selector AI assistant using the GraphRAG framework. "
            "Your primary task is to determine the appropriate search tool to call based on the user's query. "
            "For specific, detailed information about particular entities or relationships, call the 'local_search' function. "
            "For broader, abstract questions requiring a comprehensive understanding of the dataset, call the 'global_search' function. "
            "Do not attempt to answer the query directly; focus solely on selecting and calling the correct function."
        )
    )

    # Set up the team
    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)
    team = RoundRobinGroupChat(
        participants=[assistant_agent],
        termination_condition=termination
    )

    # Run a sample query
    query = "What does the station-master says about Dr. Becher?"
    print(f"\nQuery: {query}")
    
    response_stream = team.run_stream(task=query)
    async for msg in response_stream:
        if hasattr(msg, "content"):
            print(f"\nAgent response: {msg.content}")


if __name__ == "__main__":
    asyncio.run(main())

