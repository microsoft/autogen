from typing import List, cast

import chainlit as cl
import yaml

import asyncio
import json
from dataclasses import dataclass
from typing import List

from autogen_core import (
    AgentId,
    FunctionCall,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    message_handler,
    CancellationToken
)
from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage
)
from autogen_core.tools import FunctionTool, Tool
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import AssistantMessage, ChatCompletionClient, SystemMessage, UserMessage


class WeatherAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, tool_schema: List[Tool]) -> None:
            super().__init__("An agent with a weather tool")
            self._system_messages: List[LLMMessage] = [SystemMessage(content="You are a helpful AI assistant.")]
            self._model_client = model_client
            self._tools = tool_schema
            self._model_context = BufferedChatCompletionContext(buffer_size=5)




class FoodAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, tool_schema: List[Tool]) -> None:
            super().__init__("An agent with a food tool")
            self._system_messages: List[LLMMessage] = [SystemMessage(content="You are a helpful AI assistant.")]
            self._model_client = model_client
            self._tools = tool_schema
            self._model_context = BufferedChatCompletionContext(buffer_size=5)

class DateAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, tool_schema: List[Tool]) -> None:
            super().__init__("An agent with a date tool")
            self._system_messages: List[LLMMessage] = [SystemMessage(content="You are a helpful AI assistant.")]
            self._model_client = model_client
            self._tools = tool_schema
            self._model_context = BufferedChatCompletionContext(buffer_size=5)