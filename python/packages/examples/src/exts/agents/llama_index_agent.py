import os
from dataclasses import dataclass
from typing import List, Optional, Sequence
from pydantic import Field

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, MessageContext
from autogen_core.components import RoutedAgent, message_handler
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from llama_index.core import Settings
from llama_index.core.agent import ReActAgent
from llama_index.core.agent.runner.base import AgentRunner
from llama_index.core.base.llms.types import (
    ChatMessage as LlamaChatMessage,
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
from llama_index.llms.ollama import Ollama

from llama_index.core.tools import FunctionTool
from autogen_agentchat.agents import CodingAssistantAgent
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import TaskResult, TerminationCondition
from autogen_core.base import CancellationToken
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer

from autogen_agentchat.messages import (
    ChatMessage,
    HandoffMessage,
    ResetMessage,
    StopMessage,
    TextMessage,
)

from autogen_core.components.models import (
    AssistantMessage,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
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

class LLamaAssistantAgent(BaseChatAgent):

    def __init__(self, name:str,description: str, llama_index_agent: AgentRunner, memory: BaseMemory | None = None) -> None:
        super().__init__(description, llama_index_agent, memory)
        self.name = name
        self.description = description
        self.llama_agent = llama_index_agent
        if memory is None:
            self._history = ChatMemoryBuffer.from_defaults()
        else :
            self._history = memory

    

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
         # Add messages to the model context.
        for msg in messages:
            if isinstance(msg, ResetMessage):
                self.llama_agent.memory.reset()
            else:
                await self._history.aput(LlamaChatMessage(content=msg.content,role=MessageRole.USER))

        # Generate an inference result based on the current model context.
        #llm_messages = self._system_messages + self._model_context
        result = await self.llama_agent.achat(
            message=messages[-1].content,
        #    history_messages=self._memory.get_all(),
        )

        # Add the response to the model context.
        #self._memory.aput(LlamaChatMessage(content=result.response,role=MessageRole.USER))
        #self._model_context.append(AssistantMessage(content=result.content, source=self.name))

        assert isinstance(result.response, str)
        # Detect stop request.
        request_stop = "terminate" in result.response.strip().lower()
        if request_stop:
            return StopMessage(content=result.response, source=self.name)

        return TextMessage(content=result.response, source=self.name)

    async def run(
        self,
        task: str,
        *,
        cancellation_token: CancellationToken | None = None,
        termination_condition: TerminationCondition | None = None,
    ) -> TaskResult:
        """Run the agent with the given task and return the result."""
        agentResp:AgentChatResponse = await self.llama_agent.achat(task)
        # Handle the response from the llama_index_agent
        return TaskResult([ChatMessage(content=agentResp.response)])
