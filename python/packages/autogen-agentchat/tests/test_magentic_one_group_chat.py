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
from autogen_agentchat.logging import FileLogHandler
from autogen_agentchat.messages import (
    ChatMessage,
    TextMessage,
)
from autogen_agentchat.teams import (
    MagenticOneGroupChat,
)
from autogen_core.base import CancellationToken
from autogen_ext.models import ReplayChatCompletionClient

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
