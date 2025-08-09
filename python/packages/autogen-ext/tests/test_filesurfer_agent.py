import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, AsyncGenerator, List

import aiofiles
import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.messages import TextMessage
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.models.openai import OpenAIChatCompletionClient
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_function_tool_call import (
    ChatCompletionMessageFunctionToolCall as _FuncToolCall,
)
from openai.types.chat.chat_completion_message_function_tool_call import (
    Function,
)
from openai.types.completion_usage import CompletionUsage
from pydantic import BaseModel

# Ensure constructible type for tool_calls in tests
ChatCompletionMessageToolCall = _FuncToolCall  # type: ignore[assignment]


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
logger.addHandler(FileLogHandler("test_filesurfer_agent.log"))


@pytest.mark.asyncio
async def test_run_filesurfer(monkeypatch: pytest.MonkeyPatch) -> None:
    # Create a test file
    test_file = os.path.abspath("test_filesurfer_agent.html")
    async with aiofiles.open(test_file, "wt") as file:
        await file.write("""<html>
  <head>
    <title>FileSurfer test file</title>
  </head>
  <body>
    <h1>FileSurfer test H1</h1>
    <p>FileSurfer test body</p>
  </body>
</html>""")

    # Mock the API calls
    model = "gpt-4.1-nano-2025-04-14"
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
                                    name="open_path",
                                    arguments=json.dumps({"path": test_file}),
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
                                    name="open_path",
                                    arguments=json.dumps({"path": os.path.dirname(test_file)}),
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
    agent = FileSurfer(
        "FileSurfer",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
    )

    # Get the FileSurfer to read the file, and the directory
    assert agent._name == "FileSurfer"  # pyright: ignore[reportPrivateUsage]
    result = await agent.run(task="Please read the test file")
    assert isinstance(result.messages[1], TextMessage)
    assert "# FileSurfer test H1" in result.messages[1].content

    result = await agent.run(task="Please read the test directory")
    assert isinstance(result.messages[1], TextMessage)
    assert "# Index of " in result.messages[1].content
    assert "test_filesurfer_agent.html" in result.messages[1].content


@pytest.mark.asyncio
async def test_file_surfer_serialization() -> None:
    """Test that FileSurfer can be serialized and deserialized properly."""
    model = "gpt-4.1-nano-2025-04-14"
    agent = FileSurfer(
        "FileSurfer",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
    )

    # Serialize the agent
    serialized_agent = agent.dump_component()

    # Deserialize the agent
    deserialized_agent = FileSurfer.load_component(serialized_agent)

    # Check that the deserialized agent has the same attributes as the original agent
    assert isinstance(deserialized_agent, FileSurfer)
