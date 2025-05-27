import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, List

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.messages import (
    MultiModalMessage,
    TextMessage,
)
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.models.openai import OpenAIChatCompletionClient
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.completion_usage import CompletionUsage
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
                    "message": record.msg.model_dump_json(indent=2),
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
async def test_run_websurfer(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4.1-nano-2025-04-14"
    chat_completions = [
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
                    finish_reason="tool_calls",
                    index=0,
                    message=ChatCompletionMessage(
                        content=None,
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="1",
                                type="function",
                                function=Function(
                                    name="sleep",
                                    arguments=json.dumps({"reasoning": "sleep is important"}),
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
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    agent = MultimodalWebSurfer(
        "WebSurfer", model_client=OpenAIChatCompletionClient(model=model, api_key=""), use_ocr=False
    )
    # Before lazy init
    assert agent._name == "WebSurfer"  # pyright: ignore[reportPrivateUsage]
    assert agent._playwright is None  # pyright: ignore[reportPrivateUsage]
    # After lazy init
    result = await agent.run(task="task")
    assert agent._playwright is not None  # pyright: ignore[reportPrivateUsage]
    assert agent._page is not None  # pyright: ignore[reportPrivateUsage]
    # now check result object
    assert len(result.messages) == 3
    # user message
    assert isinstance(result.messages[0], TextMessage)
    assert result.messages[0].models_usage is None
    # inner message
    assert isinstance(result.messages[1], TextMessage)
    # final return
    assert isinstance(result.messages[2], TextMessage)
    assert result.messages[2].models_usage is not None
    assert result.messages[2].models_usage.completion_tokens == 5
    assert result.messages[2].models_usage.prompt_tokens == 10
    assert result.messages[2].content == "Hello"
    # check internal web surfer state
    assert len(agent._chat_history) == 2  # pyright: ignore[reportPrivateUsage]
    assert agent._chat_history[0].content == "task"  # pyright: ignore[reportPrivateUsage]
    assert agent._chat_history[1].content == "Hello"  # pyright: ignore[reportPrivateUsage]
    url_after_no_tool = agent._page.url  # pyright: ignore[reportPrivateUsage]

    # run again
    result = await agent.run(task="task")
    assert len(result.messages) == 3
    assert isinstance(result.messages[2], MultiModalMessage)
    assert (
        result.messages[2]  # type: ignore
        .content[0]  # type: ignore
        .startswith(  # type: ignore
            "I am waiting a short period of time before taking further action."
        )
    )  # type: ignore
    url_after_sleep = agent._page.url  # type: ignore
    assert url_after_no_tool == url_after_sleep


@pytest.mark.asyncio
async def test_run_websurfer_declarative(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4.1-nano-2025-04-14"
    chat_completions = [
        ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(content="Response to message 3", role="assistant"),
                )
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)

    agent = MultimodalWebSurfer(
        "WebSurfer", model_client=OpenAIChatCompletionClient(model=model, api_key=""), use_ocr=False
    )

    agent_config = agent.dump_component()
    assert agent_config.provider == "autogen_ext.agents.web_surfer.MultimodalWebSurfer"
    assert agent_config.config["name"] == "WebSurfer"

    loaded_agent = MultimodalWebSurfer.load_component(agent_config)
    assert isinstance(loaded_agent, MultimodalWebSurfer)
    assert loaded_agent.name == "WebSurfer"
