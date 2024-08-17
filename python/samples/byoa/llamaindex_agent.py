"""
This example shows how integrate llamaindex agent.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import List, Optional

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import MessageContext
from llama_index.core import Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.agent.runner.base import AgentRunner
from llama_index.core.base.llms.types import (
    ChatMessage,
    MessageRole,
)
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.memory import ChatSummaryMemoryBuffer
from llama_index.core.memory.types import BaseMemory
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.tools.wikipedia import WikipediaToolSpec


@dataclass
class Resource:
    content: str
    node_id: str
    score: Optional[float] = None


@dataclass
class Message:
    content: str
    sources: Optional[List[Resource]] = None


class LlamaIndexAgent(TypeRoutedAgent):
    def __init__(self, description: str, llama_index_agent: AgentRunner, memory: BaseMemory | None = None) -> None:
        super().__init__(description)

        self._llama_index_agent = llama_index_agent
        self._memory = memory

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        # retriever history messages from memory!
        history_messages: List[ChatMessage] = []

        # type: ignore
        # pyright: ignore
        response: AgentChatResponse  # pyright: ignore
        if self._memory is not None:
            history_messages = self._memory.get(input=message.content)

            response = await self._llama_index_agent.achat(message=message.content, history_messages=history_messages)  # pyright: ignore
        else:
            response = await self._llama_index_agent.achat(message=message.content)  # pyright: ignore

        if isinstance(response, AgentChatResponse):
            if self._memory is not None:
                self._memory.put(ChatMessage(role=MessageRole.USER, content=message.content))
                self._memory.put(ChatMessage(role=MessageRole.ASSISTANT, content=response.response))

            assert isinstance(response.response, str)

            resources: List[Resource] = [
                Resource(content=source_node.get_text(), score=source_node.score, node_id=source_node.id_)
                for source_node in response.source_nodes
            ]

            tools: List[Resource] = [
                Resource(content=source.content, node_id=source.tool_name) for source in response.sources
            ]

            resources.extend(tools)
            return Message(content=response.response, sources=resources)
        else:
            return Message(content="I'm sorry, I don't have an answer for you.")


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()

    # setup llamaindex
    llm = AzureOpenAI(
        deployment_name=os.environ.get("AZURE_OPENAI_MODEL", ""),
        temperature=0.0,
        api_key=os.environ.get("AZURE_OPENAI_KEY", ""),
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", ""),
    )

    embed_model = AzureOpenAIEmbedding(
        deployment_name=os.environ.get("AZURE_OPENAI_EMBEDDING_MODEL", ""),
        temperature=0.0,
        api_key=os.environ.get("AZURE_OPENAI_KEY", ""),
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", ""),
    )

    Settings.llm = llm
    Settings.embed_model = embed_model

    # create a react agent to use wikipedia tool
    # Get the wikipedia tool spec for llamaindex agents

    wiki_spec = WikipediaToolSpec()
    wikipedia_tool = wiki_spec.to_tool_list()[1]

    # create a memory buffer for the react agent
    memory = ChatSummaryMemoryBuffer(llm=llm, token_limit=16000)

    # create the agent using the ReAct agent pattern
    llama_index_agent = ReActAgent.from_tools(
        tools=[wikipedia_tool], llm=llm, max_iterations=8, memory=memory, verbose=True
    )

    agent = await runtime.register_and_get(
        "chat_agent",
        lambda: LlamaIndexAgent("Chat agent", llama_index_agent=llama_index_agent),
    )

    run_context = runtime.start()

    # Send a message to the agent and get the response.
    message = Message(content="What are the best movies from studio Ghibli?")
    response = await runtime.send_message(message, agent)
    assert isinstance(response, Message)
    print(response.content)

    if response.sources is not None:
        for source in response.sources:
            print(source.content)

    await run_context.stop()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
