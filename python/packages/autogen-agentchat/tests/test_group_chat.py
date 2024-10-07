import asyncio
import json
import tempfile
from typing import Any, AsyncGenerator, List, Sequence

import pytest
from autogen_agentchat.agents import (
    BaseChatAgent,
    ChatMessage,
    CodeExecutorAgent,
    CodingAssistantAgent,
    ToolUseAssistantAgent,
)
from autogen_agentchat.teams.group_chat import RoundRobinGroupChat
from autogen_core.base import CancellationToken
from autogen_core.components import FunctionCall
from autogen_core.components.code_executor import LocalCommandLineCodeExecutor
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


class _EchoAgent(BaseChatAgent):
    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> ChatMessage:
        return messages[-1]


def _pass_function(input: str) -> str:
    return "pass"


@pytest.mark.asyncio
async def test_round_robin_group_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    model = "gpt-4o-2024-05-13"
    chat_completions = [
        ChatCompletion(
            id="id1",
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content="""Here is the program\n ```python\nprint("Hello, world!")\n```""",
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
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(content="TERMINATE", role="assistant"),
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
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor_agent = CodeExecutorAgent(
            "code_executor", code_executor=LocalCommandLineCodeExecutor(work_dir=temp_dir)
        )
        coding_assistant_agent = CodingAssistantAgent(
            "coding_assistant", model_client=OpenAIChatCompletionClient(model=model, api_key="")
        )
        team = RoundRobinGroupChat(participants=[coding_assistant_agent, code_executor_agent])
        result = await team.run("Write a program that prints 'Hello, world!'")
        expected_messages = [
            "Write a program that prints 'Hello, world!'",
            'Here is the program\n ```python\nprint("Hello, world!")\n```',
            "Hello, world!",
            "TERMINATE",
        ]
        # Normalize the messages to remove \r\n and any leading/trailing whitespace.
        normalized_messages = [
            msg.content.replace("\r\n", "\n").rstrip("\n") if isinstance(msg.content, str) else msg.content
            for msg in result.messages
        ]

        # Assert that all expected messages are in the collected messages
        assert normalized_messages == expected_messages


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
    tool = FunctionTool(_pass_function, name="pass", description="pass function")
    tool_use_agent = ToolUseAssistantAgent(
        "tool_use_agent",
        model_client=OpenAIChatCompletionClient(model=model, api_key=""),
        registered_tools=[tool],
    )
    echo_agent = _EchoAgent("echo_agent", description="echo agent")
    team = RoundRobinGroupChat(participants=[tool_use_agent, echo_agent])
    await team.run("Write a program that prints 'Hello, world!'")
    context = tool_use_agent._model_context  # pyright: ignore
    assert context[0].content == "Write a program that prints 'Hello, world!'"
    assert isinstance(context[1].content, list)
    assert isinstance(context[1].content[0], FunctionCall)
    assert context[1].content[0].name == "pass"
    assert context[1].content[0].arguments == json.dumps({"input": "pass"})
    assert isinstance(context[2].content, list)
    assert isinstance(context[2].content[0], FunctionExecutionResult)
    assert context[2].content[0].content == "pass"
    assert context[2].content[0].call_id == "1"
    assert context[3].content == "Hello"
