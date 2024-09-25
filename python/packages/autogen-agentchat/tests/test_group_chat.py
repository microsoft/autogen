import asyncio
import tempfile
from typing import Any, AsyncGenerator, List

import pytest
from autogen_agentchat.agents import CodeExecutorAgent, CodingAssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.components.code_executor import LocalCommandLineCodeExecutor
from autogen_core.components.models import OpenAIChatCompletionClient
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage


class _MockChatCompletion:
    def __init__(self, model: str = "gpt-4o") -> None:
        self._saved_chat_completions: List[ChatCompletion] = [
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
        self._curr_index = 0

    async def mock_create(
        self, *args: Any, **kwargs: Any
    ) -> ChatCompletion | AsyncGenerator[ChatCompletionChunk, None]:
        await asyncio.sleep(0.1)
        completion = self._saved_chat_completions[self._curr_index]
        self._curr_index += 1
        return completion


@pytest.mark.asyncio
async def test_round_robin_group_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = _MockChatCompletion(model="gpt-4o-2024-05-13")
    monkeypatch.setattr(AsyncCompletions, "create", mock.mock_create)
    with tempfile.TemporaryDirectory() as temp_dir:
        code_executor_agent = CodeExecutorAgent(
            "code_executor", code_executor=LocalCommandLineCodeExecutor(work_dir=temp_dir)
        )
        coding_assistant_agent = CodingAssistantAgent(
            "coding_assistant", model_client=OpenAIChatCompletionClient(model="gpt-4o-2024-05-13", api_key="")
        )
        team = RoundRobinGroupChat(participants=[coding_assistant_agent, code_executor_agent])
        result = await team.run("Write a program that prints 'Hello, world!'")
        assert result.result == "TERMINATE"
