import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, AsyncGenerator, List

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Handoff, TaskResult
from autogen_agentchat.messages import (
    HandoffMessage,
    MultiModalMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
)
from autogen_core import Image
from autogen_core.components.tools import FunctionTool
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.models import OpenAIChatCompletionClient
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.completion_usage import CompletionUsage
from playwright.async_api import async_playwright
from pydantic import BaseModel


class FileLogHandler(logging.Handler):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self.file_handler = logging.FileHandler(filename)

    def emit(self, record: logging.LogRecord) -> None:
        ts = datetime.fromtimestamp(record.created).isoformat()
        if isinstance(record.msg, BaseModel):
            record.msg = json.dumps(
                {
                    "timestamp": ts,
                    "message": record.msg.model_dump(),
                    "type": record.msg.__class__.__name__,
                },
            )
        self.file_handler.emit(record)


class _MockChatCompletion:
    def __init__(self, chat_completions: List[ChatCompletion]) -> None:
        self._saved_chat_completions = chat_completions
        self._curr_index = 0

    async def mock_create(
        self, *args: Any, **kwargs: Any
    ) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
        await asyncio.sleep(0.1)
        completion = self._saved_chat_completions[self._curr_index]
        self._curr_index += 1
        return completion


logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_websurfer_agent.log"))


@pytest.mark.asyncio
async def test_multimodal_websurfer_initialization() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-08-06", api_key="")
    agent = MultimodalWebSurfer(name="TestWebSurfer", model_client=model_client)
    assert agent.name == "TestWebSurfer"
    assert agent._model_client == model_client


@pytest.mark.asyncio
async def test_run_with_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="tool_calls",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function(
                                    name="_pass_function",
                                    arguments=json.dumps({"input": "task"}),
                                ),
                            )
                        ],
                        role="assistant",
                    ),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="Hello", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(
                    finish_reason="stop", index=0, message=ChatCompletionMessage(content="TERMINATE", role="assistant")
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    agent = AssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
    )
    await agent.run(task="task")
