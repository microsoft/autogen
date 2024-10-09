import asyncio
import random
from dataclasses import dataclass
from typing import List

import pytest
from autogen_agentchat.teams._group_chat._sequential_routed_agent import SequentialRoutedAgent
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, MessageContext
from autogen_core.components import DefaultTopicId, default_subscription, message_handler


@dataclass
class Message:
    content: str


@default_subscription
class _TestAgent(SequentialRoutedAgent):
    def __init__(self, description: str) -> None:
        super().__init__(description=description)
        self.messages: List[Message] = []

    @message_handler
    async def handle_content_publish(self, message: Message, ctx: MessageContext) -> None:
        # Sleep a random amount of time to simulate processing time.
        await asyncio.sleep(random.random() / 100)
        self.messages.append(message)


@pytest.mark.asyncio
async def test_sequential_routed_agent() -> None:
    runtime = SingleThreadedAgentRuntime()
    runtime.start()
    await _TestAgent.register(runtime, type="test_agent", factory=lambda: _TestAgent(description="Test Agent"))
    test_agent_id = AgentId(type="test_agent", key="default")
    for i in range(100):
        await runtime.publish_message(Message(content=f"{i}"), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()
    test_agent = await runtime.try_get_underlying_agent_instance(test_agent_id, _TestAgent)
    for i in range(100):
        assert test_agent.messages[i].content == f"{i}"
