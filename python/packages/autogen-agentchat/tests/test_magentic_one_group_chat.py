import asyncio
import json
import logging
from typing import List, Sequence

import pytest
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import (
    BaseChatAgent,
)
from autogen_agentchat.base import Response
from autogen_agentchat.messages import (
    ChatMessage,
    TextMessage,
)
from autogen_agentchat.teams import (
    MagenticOneGroupChat,
)
from autogen_core.base import CancellationToken
from autogen_ext.models import ReplayChatCompletionClient
from utils import FileLogHandler

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.addHandler(FileLogHandler("test_magentic_one_group_chat.log"))


class _EchoAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name, description)
        self._last_message: str | None = None
        self._total_messages = 0

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        return [TextMessage]

    @property
    def total_messages(self) -> int:
        return self._total_messages

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        if len(messages) > 0:
            assert isinstance(messages[0], TextMessage)
            self._last_message = messages[0].content
            self._total_messages += 1
            return Response(chat_message=TextMessage(content=messages[0].content, source=self.name))
        else:
            assert self._last_message is not None
            self._total_messages += 1
            return Response(chat_message=TextMessage(content=self._last_message, source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        self._last_message = None


@pytest.mark.asyncio
async def test_magentic_one_group_chat_cancellation() -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")

    model_client = ReplayChatCompletionClient(
        chat_completions=["test", "test", json.dumps({"is_request_satisfied": {"answer": True, "reason": "test"}})],
    )

    # Set max_turns to a large number to avoid stopping due to max_turns before cancellation.
    team = MagenticOneGroupChat(participants=[agent_1, agent_2, agent_3, agent_4], model_client=model_client)
    cancellation_token = CancellationToken()
    run_task = asyncio.create_task(
        team.run(
            task="Write a program that prints 'Hello, world!'",
            cancellation_token=cancellation_token,
        )
    )

    # Cancel the task.
    cancellation_token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run_task


@pytest.mark.asyncio
async def test_magentic_one_group_chat_basic() -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")

    model_client = ReplayChatCompletionClient(
        chat_completions=[
            "No facts",
            "No plan",
            json.dumps(
                {
                    "is_request_satisfied": {"answer": False, "reason": "test"},
                    "is_progress_being_made": {"answer": True, "reason": "test"},
                    "is_in_loop": {"answer": False, "reason": "test"},
                    "instruction_or_question": {"answer": "Continue task", "reason": "test"},
                    "next_speaker": {"answer": "agent_1", "reason": "test"},
                }
            ),
            json.dumps(
                {
                    "is_request_satisfied": {"answer": True, "reason": "Because"},
                    "is_progress_being_made": {"answer": True, "reason": "test"},
                    "is_in_loop": {"answer": False, "reason": "test"},
                    "instruction_or_question": {"answer": "Task completed", "reason": "Because"},
                    "next_speaker": {"answer": "agent_1", "reason": "test"},
                }
            ),
            "print('Hello, world!')",
        ],
    )

    team = MagenticOneGroupChat(participants=[agent_1, agent_2, agent_3, agent_4], model_client=model_client)
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 5
    assert result.messages[2].content == "Continue task"
    assert result.messages[4].content == "print('Hello, world!')"
    assert result.stop_reason is not None and result.stop_reason == "Because"


@pytest.mark.asyncio
async def test_magentic_one_group_chat_with_stalls() -> None:
    agent_1 = _EchoAgent("agent_1", description="echo agent 1")
    agent_2 = _EchoAgent("agent_2", description="echo agent 2")
    agent_3 = _EchoAgent("agent_3", description="echo agent 3")
    agent_4 = _EchoAgent("agent_4", description="echo agent 4")

    model_client = ReplayChatCompletionClient(
        chat_completions=[
            "No facts",
            "No plan",
            json.dumps(
                {
                    "is_request_satisfied": {"answer": False, "reason": "test"},
                    "is_progress_being_made": {"answer": False, "reason": "test"},
                    "is_in_loop": {"answer": True, "reason": "test"},
                    "instruction_or_question": {"answer": "Stalling", "reason": "test"},
                    "next_speaker": {"answer": "agent_1", "reason": "test"},
                }
            ),
            json.dumps(
                {
                    "is_request_satisfied": {"answer": False, "reason": "test"},
                    "is_progress_being_made": {"answer": False, "reason": "test"},
                    "is_in_loop": {"answer": True, "reason": "test"},
                    "instruction_or_question": {"answer": "Stalling again", "reason": "test"},
                    "next_speaker": {"answer": "agent_2", "reason": "test"},
                }
            ),
            "No facts2",
            "No plan2",
            json.dumps(
                {
                    "is_request_satisfied": {"answer": True, "reason": "test"},
                    "is_progress_being_made": {"answer": True, "reason": "test"},
                    "is_in_loop": {"answer": False, "reason": "test"},
                    "instruction_or_question": {"answer": "Task completed", "reason": "test"},
                    "next_speaker": {"answer": "agent_3", "reason": "test"},
                }
            ),
            "print('Hello, world!')",
        ],
    )

    team = MagenticOneGroupChat(
        participants=[agent_1, agent_2, agent_3, agent_4], model_client=model_client, max_stalls=2
    )
    result = await team.run(task="Write a program that prints 'Hello, world!'")
    assert len(result.messages) == 6
    assert isinstance(result.messages[1].content, str)
    assert result.messages[1].content.startswith("\nWe are working to address the following user request:")
    assert isinstance(result.messages[4].content, str)
    assert result.messages[4].content.startswith("\nWe are working to address the following user request:")
    assert result.stop_reason is not None and result.stop_reason == "test"
