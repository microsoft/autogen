import asyncio
import json
from typing import Any, AsyncGenerator, List

import pytest
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, CancellationToken
from autogen_core.components import FunctionCall
from autogen_core.components.models import (
    AssistantMessage,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    OpenAIChatCompletionClient,
    UserMessage,
)
from autogen_core.components.tool_agent import (
    InvalidToolArgumentsException,
    ToolAgent,
    ToolExecutionException,
    ToolNotFoundException,
    tool_agent_caller_loop,
)
from autogen_core.components.tools import FunctionTool, Tool
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.completion_usage import CompletionUsage


def _pass_function(input: str) -> str:
    return "pass"


def _raise_function(input: str) -> str:
    raise Exception("raise")


async def _async_sleep_function(input: str) -> str:
    await asyncio.sleep(10)
    return "pass"


class _MockChatCompletion:
    def __init__(self, model: str = "gpt-4o") -> None:
        self._saved_chat_completions: List[ChatCompletion] = [
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
                    Choice(
                        finish_reason="stop", index=0, message=ChatCompletionMessage(content="Hello", role="assistant")
                    )
                ],
                created=0,
                model=model,
                object="chat.completion",
                usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            ),
        ]
        self._curr_index = 0

    async def mock_create(
        self, *args: Any, **kwargs: Any
    ) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
        await asyncio.sleep(0.1)
        completion = self._saved_chat_completions[self._curr_index]
        self._curr_index += 1
        return completion


@pytest.mark.asyncio
async def test_tool_agent() -> None:
    runtime = SingleThreadedAgentRuntime()
    await runtime.register(
        "tool_agent",
        lambda: ToolAgent(
            description="Tool agent",
            tools=[
                FunctionTool(_pass_function, name="pass", description="Pass function"),
                FunctionTool(_raise_function, name="raise", description="Raise function"),
                FunctionTool(_async_sleep_function, name="sleep", description="Sleep function"),
            ],
        ),
    )
    agent = AgentId("tool_agent", "default")
    runtime.start()

    # Test pass function
    result = await runtime.send_message(
        FunctionCall(id="1", arguments=json.dumps({"input": "pass"}), name="pass"), agent
    )
    assert result == FunctionExecutionResult(call_id="1", content="pass")

    # Test raise function
    with pytest.raises(ToolExecutionException):
        await runtime.send_message(FunctionCall(id="2", arguments=json.dumps({"input": "raise"}), name="raise"), agent)

    # Test invalid tool name
    with pytest.raises(ToolNotFoundException):
        await runtime.send_message(FunctionCall(id="3", arguments=json.dumps({"input": "pass"}), name="invalid"), agent)

    # Test invalid arguments
    with pytest.raises(InvalidToolArgumentsException):
        await runtime.send_message(FunctionCall(id="3", arguments="invalid json /xd", name="pass"), agent)

    # Test sleep and cancel.
    token = CancellationToken()
    result_future = runtime.send_message(
        FunctionCall(id="3", arguments=json.dumps({"input": "sleep"}), name="sleep"), agent, cancellation_token=token
    )
    token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await result_future

    await runtime.stop()


@pytest.mark.asyncio
async def test_caller_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = _MockChatCompletion(model="gpt-4o-2024-05-13")
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    client = OpenAIChatCompletionClient(model="gpt-4o-2024-05-13", api_key="api_key")
    tools: List[Tool] = [FunctionTool(_pass_function, name="pass", description="Pass function")]
    runtime = SingleThreadedAgentRuntime()
    await runtime.register(
        "tool_agent",
        lambda: ToolAgent(
            description="Tool agent",
            tools=tools,
        ),
    )
    agent = AgentId("tool_agent", "default")
    runtime.start()
    messages = await tool_agent_caller_loop(
        runtime, agent, client, [UserMessage(content="Hello", source="user")], tool_schema=tools
    )
    assert len(messages) == 3
    assert isinstance(messages[0], AssistantMessage)
    assert isinstance(messages[1], FunctionExecutionResultMessage)
    assert isinstance(messages[2], AssistantMessage)
    await runtime.stop()
