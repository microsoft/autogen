# DuckDuckGo Search Agent created by Varad Srivastava
from typing import Any, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient

from autogen_ext.tools.web_search import DuckDuckGoSearchTool


class DuckDuckGoSearchAgent(AssistantAgent):
    """
    A specialized AssistantAgent that uses DuckDuckGo for web searches.

    This agent is designed to perform web searches using DuckDuckGo and provide
    relevant information based on the search results. It can be used in group chats
    or as a standalone agent for research and information gathering tasks.

    The agent comes pre-configured with a DuckDuckGo search tool and a system message
    optimized for research tasks.

    Example:
        .. code-block:: python

            from autogen_ext.agents.duckduckgo_search import DuckDuckGoSearchAgent
            from autogen_ext.models.openai import OpenAIChatCompletionClient

            # Create a model client
            model_client = OpenAIChatCompletionClient(model="gpt-4")

            # Create a DuckDuckGo search agent
            search_agent = DuckDuckGoSearchAgent(
                name="researcher",
                model_client=model_client,
            )

            # Use the agent
            result = await search_agent.run(task="What are the latest developments in AI?")
            print(result.messages[-1].content)
    """

    DEFAULT_DESCRIPTION = "A research assistant that uses DuckDuckGo to find and analyze information from the web."

    DEFAULT_SYSTEM_MESSAGE = """You are a research assistant that uses DuckDuckGo to find accurate information.

When conducting research:
1. Break down complex queries into specific, targeted search terms
2. Use the duckduckgo_search tool to find relevant information
3. Analyze and synthesize information from multiple sources when possible
4. Explain why the information is relevant and how it connects to the query
5. Cite your sources when providing information
6. If you're unsure about something, say so and explain why
7. Provide clear, well-structured responses with key findings highlighted
"""

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        description: Optional[str] = None,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a DuckDuckGo Search Agent.

        Args:
            name (str): The name of the agent
            model_client (ChatCompletionClient): The model client to use for generating responses
            description (Optional[str]): A description of the agent's capabilities. If not provided,
                a default description will be used.
            system_message (Optional[str]): The system message to use for the agent. If not provided,
                a default message will be used.
            **kwargs: Additional keyword arguments passed to the parent AssistantAgent
        """
        if description is None:
            description = self.DEFAULT_DESCRIPTION

        if system_message is None:
            system_message = self.DEFAULT_SYSTEM_MESSAGE

        # Create the DuckDuckGo search tool
        search_tool = DuckDuckGoSearchTool()

        # Initialize the parent AssistantAgent with the search tool
        super().__init__(
            name=name,
            model_client=model_client,
            description=description,
            system_message=system_message,
            tools=[search_tool],
            **kwargs,
        )
