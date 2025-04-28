from typing import AsyncGenerator, List, Literal, Optional, Sequence, Union

from autogen_core import CancellationToken, Component, ComponentModel
from pydantic import BaseModel

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

# ------------------------------
# Message Filter Config
# ------------------------------


class PerSourceFilter(BaseModel):
    source: str
    position: Optional[Literal["first", "last"]] = None
    count: Optional[int] = None


class MessageFilterConfig(BaseModel):
    per_source: List[PerSourceFilter]


# ------------------------------
# Component Config
# ------------------------------


class MessageFilterAgentConfig(BaseModel):
    name: str
    wrapped_agent: ComponentModel
    filter: MessageFilterConfig


# ------------------------------
# Message Filter Agent
# ------------------------------


class MessageFilterAgent(BaseChatAgent, Component[MessageFilterAgentConfig]):
    """
    A wrapper agent that filters incoming messages before passing them to the inner agent.

    This is useful in scenarios like multi-agent workflows where an agent should only
    process a subset of the full message history—for example, only the last message
    from each upstream agent, or only the first message from a specific source.

    Filtering is configured using `MessageFilterConfig`, which supports:
    - Filtering by message source (e.g., only messages from "user" or another agent)
    - Selecting the first N or last N messages from each source
    - If position is `None`, all messages from that source are included

    This agent is compatible with both direct message passing and team-based execution
    such as `AGGraph`.

    Example:
        >>> agent_a = MessageFilterAgent(
        ...     name="A",
        ...     wrapped_agent=some_other_agent,
        ...     filter=MessageFilterConfig(
        ...         per_source=[
        ...             PerSourceFilter(source="user", position="first", count=1),
        ...             PerSourceFilter(source="B", position="last", count=2),
        ...         ]
        ...     ),
        ... )

    Example use case with AGGraph:
        Suppose you have a looping multi-agent graph: A → B → A → B → C.

        You want:
        - A to only see the user message and the last message from B
        - B to see the user message, last message from A, and its own prior responses (for reflection)
        - C to see the user message and the last message from B

        Wrap the agents like so:

        >>> agent_a = MessageFilterAgent(
        ...     name="A",
        ...     wrapped_agent=agent_a_inner,
        ...     filter=MessageFilterConfig(
        ...         per_source=[
        ...             PerSourceFilter(source="user", position="first", count=1),
        ...             PerSourceFilter(source="B", position="last", count=1),
        ...         ]
        ...     ),
        ... )

        >>> agent_b = MessageFilterAgent(
        ...     name="B",
        ...     wrapped_agent=agent_b_inner,
        ...     filter=MessageFilterConfig(
        ...         per_source=[
        ...             PerSourceFilter(source="user", position="first", count=1),
        ...             PerSourceFilter(source="A", position="last", count=1),
        ...             PerSourceFilter(source="B", position="last", count=10),
        ...         ]
        ...     ),
        ... )

        >>> agent_c = MessageFilterAgent(
        ...     name="C",
        ...     wrapped_agent=agent_c_inner,
        ...     filter=MessageFilterConfig(
        ...         per_source=[
        ...             PerSourceFilter(source="user", position="first", count=1),
        ...             PerSourceFilter(source="B", position="last", count=1),
        ...         ]
        ...     ),
        ... )

        Then define the graph:

        >>> graph = DiGraph(
        ...     nodes={
        ...         "A": DiGraphNode(name="A", edges=[DiGraphEdge(target="B")]),
        ...         "B": DiGraphNode(
        ...             name="B",
        ...             edges=[
        ...                 DiGraphEdge(target="C", condition="exit"),
        ...                 DiGraphEdge(target="A", condition="loop"),
        ...             ],
        ...         ),
        ...         "C": DiGraphNode(name="C", edges=[]),
        ...     },
        ...     default_start_node="A",
        ... )

        This will ensure each agent sees only what is needed for its decision or action logic.
    """

    component_config_schema = MessageFilterAgentConfig
    component_provider_override = "autogen_agentchat.teams.MessageFilterAgent"

    def __init__(
        self,
        name: str,
        wrapped_agent: BaseChatAgent,
        filter: MessageFilterConfig,
    ):
        super().__init__(name=name, description=f"{wrapped_agent.description} (with message filtering)")
        self._wrapped_agent = wrapped_agent
        self._filter = filter

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return self._wrapped_agent.produced_message_types

    def _apply_filter(self, messages: Sequence[BaseChatMessage]) -> Sequence[BaseChatMessage]:
        result: List[BaseChatMessage] = []

        for source_filter in self._filter.per_source:
            msgs = [m for m in messages if m.source == source_filter.source]

            if source_filter.position == "first" and source_filter.count:
                msgs = msgs[: source_filter.count]
            elif source_filter.position == "last" and source_filter.count:
                msgs = msgs[-source_filter.count :]

            result.extend(msgs)

        return result

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        filtered = self._apply_filter(messages)
        return await self._wrapped_agent.on_messages(filtered, cancellation_token)

    async def on_messages_stream(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> AsyncGenerator[Union[BaseAgentEvent, BaseChatMessage, Response], None]:
        filtered = self._apply_filter(messages)
        async for item in self._wrapped_agent.on_messages_stream(filtered, cancellation_token):
            yield item

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        await self._wrapped_agent.on_reset(cancellation_token)

    def _to_config(self) -> MessageFilterAgentConfig:
        return MessageFilterAgentConfig(
            name=self.name,
            wrapped_agent=self._wrapped_agent.dump_component(),
            filter=self._filter,
        )

    @classmethod
    def _from_config(cls, config: MessageFilterAgentConfig) -> "MessageFilterAgent":
        wrapped = BaseChatAgent.load_component(config.wrapped_agent)
        return cls(
            name=config.name,
            wrapped_agent=wrapped,
            filter=config.filter,
        )
