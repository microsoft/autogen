from typing import Sequence

from autogen_agentchat.agents import BaseChatAgent, MessageFilterAgent
from autogen_agentchat.agents._message_filter_agent import MessageFilterConfig, PerSourceFilter
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_core import CancellationToken


class _DummyAgent(BaseChatAgent):
    """Minimal agent used only to satisfy MessageFilterAgent's wrapped_agent requirement."""

    def __init__(self, name: str = "dummy") -> None:
        super().__init__(name=name, description="dummy")

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken) -> Response:
        return Response(chat_message=TextMessage(content="ok", source=self.name))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass


def _make_messages(source: str, n: int) -> list[TextMessage]:
    return [TextMessage(content=f"msg-{i}", source=source) for i in range(n)]


def _apply(
    per_source: Sequence[PerSourceFilter],
    messages: Sequence[BaseChatMessage],
) -> list[BaseChatMessage]:
    agent = MessageFilterAgent(
        name="filter",
        wrapped_agent=_DummyAgent(),
        filter=MessageFilterConfig(per_source=list(per_source)),
    )
    return list(agent._apply_filter(messages))  # pyright: ignore[reportPrivateUsage]


def test_count_zero_returns_no_messages_first() -> None:
    # Regression test: count=0 with position="first" must return zero messages,
    # not all messages from that source. Previously the truthiness check
    # (`and source_filter.count`) treated 0 the same as None and skipped slicing.
    messages = _make_messages("user", 3)
    result = _apply([PerSourceFilter(source="user", position="first", count=0)], messages)
    assert result == []


def test_count_zero_returns_no_messages_last() -> None:
    messages = _make_messages("user", 3)
    result = _apply([PerSourceFilter(source="user", position="last", count=0)], messages)
    assert result == []


def test_count_none_keeps_all_messages() -> None:
    # count=None (default) means "do not slice" — all messages from that source
    # are kept. This must remain unchanged by the fix.
    messages = _make_messages("user", 3)
    result = _apply([PerSourceFilter(source="user", position="first", count=None)], messages)
    assert len(result) == 3


def test_count_positive_first_and_last() -> None:
    # Sanity check that normal positive counts still behave as before.
    messages = _make_messages("user", 5)
    first_two = _apply([PerSourceFilter(source="user", position="first", count=2)], messages)
    assert [m.to_text() for m in first_two] == ["msg-0", "msg-1"]

    last_two = _apply([PerSourceFilter(source="user", position="last", count=2)], messages)
    assert [m.to_text() for m in last_two] == ["msg-3", "msg-4"]
