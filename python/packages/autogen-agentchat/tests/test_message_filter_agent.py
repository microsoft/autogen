import pytest
from typing import List
from autogen_agentchat.agents import MessageFilterAgent, MessageFilterConfig, PerSourceFilter, BaseChatAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from typing import Sequence, Any, AsyncGenerator, Union
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

class DummyAgent(BaseChatAgent):
    def __init__(self, name: str):
        super().__init__(name=name, description="Dummy agent")
        self.received_messages: List[BaseChatMessage] = []

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        self.received_messages = list(messages)
        return Response(chat_message=TextMessage(content="dummy", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


@pytest.mark.asyncio
async def test_message_filter_agent_chronological_order() -> None:
    # 5 messages in this exact chronological order
    messages: List[BaseChatMessage] = [
        TextMessage(content="please solve X", source="user"),
        TextMessage(content="A's first attempt", source="A"),
        TextMessage(content="B's first review", source="B"),
        TextMessage(content="A's second attempt", source="A"),
        TextMessage(content="B's second review", source="B"),
    ]

    inner = DummyAgent("B_inner")
    
    # We want to keep the user's first message, A's last message, and B's last 10 messages.
    # The config list order shouldn't dictate the chronological output order.
    filtered_agent = MessageFilterAgent(
        name="B",
        wrapped_agent=inner,
        filter=MessageFilterConfig(per_source=[
            PerSourceFilter(source="user", position="first", count=1),
            PerSourceFilter(source="A", position="last", count=1),
            PerSourceFilter(source="B", position="last", count=10),
        ]),
    )

    await filtered_agent.on_messages(messages, CancellationToken())
    
    # Verify strict chronological preservation: User (t0) -> B's 1st (t2) -> A's 2nd (t3) -> B's 2nd (t4)
    # A's 1st attempt (t1) is dropped because we only want A's last message.
    sources = [m.source for m in inner.received_messages]
    contents = [m.content for m in inner.received_messages]
    
    assert sources == ["user", "B", "A", "B"]
    assert contents == [
        "please solve X",
        "B's first review",
        "A's second attempt",
        "B's second review"
    ]
