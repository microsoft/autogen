import os
from dataclasses import dataclass
from typing import List, Optional
from pydantic import Field

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, MessageContext
from autogen_core.components import RoutedAgent, message_handler
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
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
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.openai import OpenAI
from llama_index.tools.wikipedia import WikipediaToolSpec

from llama_index.llms.openai_like import OpenAILike
from llama_index.core.tools import FunctionTool
from autogen_agentchat.agents import CodingAssistantAgent
from autogen_ext.models import OpenAIChatCompletionClient

llm = OpenAILike(model="qwen2", api_base="http://127.0.0.1:4000/v1", api_key="fake")

response = llm.complete("Hello World!")
print(str(response))

def get_weather(city: str=Field(description="城市名称")) -> str:
    """
    查询城市的天气情况
    """
    return f"The weather in {city} is 73 degrees and Sunny."
def get_model_client() -> OpenAIChatCompletionClient:
    "Mimic OpenAI API using Local LLM Server."
    return OpenAIChatCompletionClient(
        model="gpt-4o",  # Need to use one of the OpenAI models as a placeholder for now.
        api_key="NotRequiredSinceWeAreLocal",
        base_url="http://127.0.0.1:4000",
    )
@dataclass
class Resource:
    content: str
    node_id: str
    score: float = None


@dataclass
class Message:
    content: str
    sources: List[Resource] = None
@dataclass
class CriticalMsg:
    content: str


class LlamaIndexAgent(RoutedAgent):
    def __init__(self, description: str, llama_index_agent: AgentRunner, memory: BaseMemory | None = None) -> None:
        super().__init__(description)

        self._llama_index_agent = llama_index_agent
        self._memory = memory

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        # retriever history messages from memory!
        history_messages: List[ChatMessage] = []

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


async def newRuntime():
    runtime = SingleThreadedAgentRuntime()
    await LlamaIndexAgent.register(
        runtime,
        "chat_agent",
        lambda: LlamaIndexAgent(
            description="Llama Index Agent",
            llama_index_agent=ReActAgent.from_tools(
                tools=[FunctionTool.from_defaults(fn=get_weather)],
                llm=llm,
                max_iterations=8,
                memory=ChatSummaryMemoryBuffer(llm=llm, token_limit=16000),
                verbose=True,
            ),
        ),
    )

    CodingAssistantAgent.register()
    planner_agent = CodingAssistantAgent(
    "planner_agent",
    model_client=get_model_client(),
    description="你是一个消息分辨者",
    system_message="你基于客观事实和物理规律，判断信息的真假。",
    )
    runtime.start()
    agent = AgentId("chat_agent", "default")
    message = Message(content="广州的天气怎么样")
    response = await runtime.send_message(message, agent)
    assert isinstance(response, Message)
    
    return response.content



if __name__=='__main__':
    import asyncio
    result = asyncio.run(newRuntime())
    print("llama-index 响应：  ",result)