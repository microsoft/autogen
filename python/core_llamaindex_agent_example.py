"""
LlamaIndex-Backed Agent Example

This example demonstrates how to create an AI agent using LlamaIndex, integrated with the AutoGen agent runtime. The agent can use Wikipedia as a tool and respond to user queries with sources.

Requirements:
- pip install "llama-index-readers-web" "llama-index-readers-wikipedia" "llama-index-tools-wikipedia" "llama-index-embeddings-azure-openai" "llama-index-llms-azure-openai" "llama-index" "azure-identity" autogen-core autogen-ext

Run with: python python/core_llamaindex_agent_example.py
"""
import os
from typing import List, Optional

from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
from llama_index.core import Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.agent.runner.base import AgentRunner
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.memory import ChatSummaryMemoryBuffer
from llama_index.core.memory.types import BaseMemory
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.tools.wikipedia import WikipediaToolSpec
from pydantic import BaseModel

# ------------------- Message Protocol -------------------
class Resource(BaseModel):
    content: str
    node_id: str
    score: Optional[float] = None

class Message(BaseModel):
    content: str
    sources: Optional[List[Resource]] = None

# ------------------- LlamaIndex Agent -------------------
class LlamaIndexAgent(RoutedAgent):
    def __init__(self, description: str, llama_index_agent: AgentRunner, memory: BaseMemory | None = None) -> None:
        super().__init__(description)
        self._llama_index_agent = llama_index_agent
        self._memory = memory

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        history_messages: List[ChatMessage] = []
        response: AgentChatResponse
        if self._memory is not None:
            history_messages = self._memory.get(input=message.content)
            response = await self._llama_index_agent.achat(message=message.content, history_messages=history_messages)
        else:
            response = await self._llama_index_agent.achat(message=message.content)
        if isinstance(response, AgentChatResponse):
            if self._memory is not None:
                self._memory.put(ChatMessage(role=MessageRole.USER, content=message.content))
                self._memory.put(ChatMessage(role=MessageRole.ASSISTANT, content=response.response))
            assert isinstance(response.response, str)
            resources: List[Resource] = [
                Resource(content=source_node.get_text(), score=source_node.score, node_id=source_node.id_)
                for source_node in getattr(response, "source_nodes", [])
            ]
            tools: List[Resource] = [
                Resource(content=source.content, node_id=source.tool_name) for source in getattr(response, "sources", [])
            ]
            resources.extend(tools)
            return Message(content=response.response, sources=resources)
        else:
            return Message(content="I'm sorry, I don't have an answer for you.")

# ------------------- Main Example -------------------
async def main():
    # Set up LlamaIndex LLM and embedding
    llm = OpenAI(
        model="gpt-4o",
        temperature=0.0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    embed_model = OpenAIEmbedding(
        model="text-embedding-ada-002",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    Settings.llm = llm
    Settings.embed_model = embed_model
    # Create the Wikipedia tool
    wiki_spec = WikipediaToolSpec()
    wikipedia_tool = wiki_spec.to_tool_list()[1]
    # Set up the agent runtime and register the LlamaIndex agent
    runtime = SingleThreadedAgentRuntime()
    await LlamaIndexAgent.register(
        runtime,
        "chat_agent",
        lambda: LlamaIndexAgent(
            description="Llama Index Agent",
            llama_index_agent=ReActAgent.from_tools(
                tools=[wikipedia_tool],
                llm=llm,
                max_iterations=8,
                memory=ChatSummaryMemoryBuffer(llm=llm, token_limit=16000),
                verbose=True,
            ),
        ),
    )
    agent = AgentId("chat_agent", "default")
    runtime.start()
    message = Message(content="What are the best movies from studio Ghibli?")
    response = await runtime.send_message(message, agent)
    assert isinstance(response, Message)
    print(response.content)
    if response.sources is not None:
        for source in response.sources:
            print(source.content)
    await runtime.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
