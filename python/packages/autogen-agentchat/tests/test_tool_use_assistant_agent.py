import asyncio
import json
from typing import Any, AsyncGenerator, List

import pytest
from autogen_agentchat.agents import ToolUseAssistantAgent
from autogen_agentchat.messages import (
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
)
from autogen_core.base import CancellationToken
from autogen_core.components.models import FunctionExecutionResult, OpenAIChatCompletionClient
from autogen_core.components.tools import FunctionTool
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.completion_usage import CompletionUsage


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


def _pass_function(input: str) -> str:
    return "pass"


async def _fail_function(input: str) -> str:
    return "fail"


async def _echo_function(input: str) -> str:
    return input


@pytest.mark.asyncio
async def test_round_robin_group_chat_with_tools(monkeypatch: pytest.MonkeyPatch) -> None:
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
                                    name="pass",
                                    arguments=json.dumps({"input": "pass"}),
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
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
        ChatCompletion(
            id="id2",
            choices=[
                Choice(finish_reason="stop", index=0, message=ChatCompletionMessage(content="Hello", role="assistant"))
            ],
            created=0,
            model=model,
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
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
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        ),
    ]
    mock = _MockChatCompletion(chat_completions)
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    tool_use_agent = ToolUseAssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        registered_tools=[_pass_function, _fail_function, FunctionTool(_echo_function, description="Echo")],
    )
    response = await tool_use_agent.on_messages(
        messages=[TextMessage(content="Test", source="user")], cancellation_token=CancellationToken()
    )
    assert isinstance(response, ToolCallMessage)
    tool_call_results = [FunctionExecutionResult(content="", call_id=call.id) for call in response.content]

    response = await tool_use_agent.on_messages(
        messages=[ToolCallResultMessage(content=tool_call_results, source="test")],
        cancellation_token=CancellationToken(),
    )
    assert isinstance(response, TextMessage)
