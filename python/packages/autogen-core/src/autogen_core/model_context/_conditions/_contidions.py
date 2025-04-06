from typing import List, Sequence

from autogen_core import Component
from pydantic import BaseModel
from typing_extensions import Self

from ..._component_config import Component, ComponentModel
from ...tools import ToolSchema
from ...models import ChatCompletionClient, FunctionExecutionResultMessage, LLMMessage
from .._chat_completion_context import ChatCompletionContext
from ._base_condition import MessageCompletionCondition, MessageCompletionException
from ._types import ContextMessage, TriggerMessage, BaseContextMessage, LLMMessageInstance

class StopMessageCompletionConfig(BaseModel):
    pass


class StopMessageCompletion(MessageCompletionCondition, Component[StopMessageCompletionConfig]):
    """Terminate the conversation if a StopMessage is received."""

    component_config_schema = StopMessageCompletionConfig
    component_provider_override = "" # TODO

    def __init__(self) -> None:
        self._triggered = False

    @property
    def triggreed(self) -> bool:
        return self._triggered

    async def __call__(self, messages: List[ContextMessage]) -> TriggerMessage | None:
        if self._triggered:
            raise MessageCompletionException("Triggered condition has already been reached")
        for message in messages:
            if isinstance(message, TriggerMessage):
                self._triggered = True
                return TriggerMessage(content="Triggered message received", source="StopMessageCompletion")
        return None

    async def reset(self) -> None:
        self._triggered = False

    def _to_config(self) -> StopMessageCompletionConfig:
        return StopMessageCompletionConfig()

    @classmethod
    def _from_config(cls, config: StopMessageCompletionConfig) -> Self:
        return cls()


class MaxMessageCompletionConfig(BaseModel):
    max_messages: int
    include_agent_event: bool = False


class MaxMessageCompletion(MessageCompletionCondition, Component[MaxMessageCompletionConfig]):
    """Terminate the conversation after a maximum number of messages have been exchanged.

    Args:
        max_messages: The maximum number of messages allowed in the conversation.
        include_agent_event: If True, include :class:`~autogen_agentchat.messages.BaseAgentEvent` in the message count.
            Otherwise, only include :class:`~autogen_agentchat.messages.BaseChatMessage`. Defaults to False.
    """

    component_config_schema = MaxMessageCompletionConfig
    component_provider_override = "" #TODO

    def __init__(self, max_messages: int) -> None:
        self._max_messages = max_messages
        self._message_count = 0

    @property
    def triggered(self) -> bool:
        return self._message_count >= self._max_messages

    async def __call__(self, messages: List[ContextMessage]) -> TriggerMessage | None:
        if self.triggered:
            raise MessageCompletionException("Triggered condition has already been reached")
        self._message_count += len([m for m in messages if isinstance(m, BaseContextMessage)])
        if self._message_count >= self._max_messages:
            return TriggerMessage(
                content=f"Maximum number of messages {self._max_messages} reached, current message count: {self._message_count}",
                source="MaxMessageCompletion",
            )
        return None

    async def reset(self) -> None:
        self._message_count = 0

    def _to_config(self) -> MaxMessageCompletionConfig:
        return MaxMessageCompletionConfig(
            max_messages=self._max_messages
        )

    @classmethod
    def _from_config(cls, config: MaxMessageCompletionConfig) -> Self:
        return cls(max_messages=config.max_messages)


class TextMentionMessageCompletionConfig(BaseModel):
    text: str


class TextMentionMessageCompletion(MessageCompletionCondition, Component[TextMentionMessageCompletionConfig]):
    """Terminate the conversation if a specific text is mentioned.


    Args:
        text: The text to look for in the messages.
        sources: Check only messages of the specified agents for the text to look for.
    """

    component_config_schema = TextMentionMessageCompletionConfig
    component_provider_override = "" # TODO

    def __init__(self, text: str, sources: Sequence[str] | None = None) -> None:
        self._termination_text = text
        self._terminated = False
        self._sources = sources

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: List[ContextMessage]) -> TriggerMessage | None:
        if self._terminated:
            raise MessageCompletionException("Triggerd condition has already been reached")
        for message in [m for m in messages if isinstance(m, BaseContextMessage)]:
            if isinstance(message, BaseContextMessage):
                if self._sources is not None and message.source not in self._sources:
                    continue

            content = message.content
            if self._termination_text in content:
                self._terminated = True
                return TriggerMessage(
                    content=f"Text '{self._termination_text}' mentioned", source="TextMentionMessageCompletion"
                )
        return None

    async def reset(self) -> None:
        self._terminated = False

    def _to_config(self) -> TextMentionMessageCompletionConfig:
        return TextMentionMessageCompletionConfig(text=self._termination_text)

    @classmethod
    def _from_config(cls, config: TextMentionMessageCompletionConfig) -> Self:
        return cls(text=config.text)

class TokenUsageMessageCompletionConfig(BaseModel):
    model_client: ComponentModel
    token_limit: int | None = None
    tool_schema: List[ToolSchema] | None = None
    internal_messages: List[LLMMessage] | None = None


class TokenUsageMessageCompletion(MessageCompletionCondition, Component[TokenUsageMessageCompletionConfig]):
    """(Experimental) A token based chat completion context maintains a view of the context up to a token limit.

    .. note::

        Added in v0.4.10. This is an experimental component and may change in the future.

    Args:
        model_client (ChatCompletionClient): The model client to use for token counting.
            The model client must implement the :meth:`~autogen_core.models.ChatCompletionClient.count_tokens`
            and :meth:`~autogen_core.models.ChatCompletionClient.remaining_tokens` methods.
        token_limit (int | None): The maximum number of tokens to keep in the context
            using the :meth:`~autogen_core.models.ChatCompletionClient.count_tokens` method.
            If None, the context will be limited by the model client using the
            :meth:`~autogen_core.models.ChatCompletionClient.remaining_tokens` method.
        tools (List[ToolSchema] | None): A list of tool schema to use in the context.
        initial_messages (List[LLMMessage] | None): A list of initial messages to include in the context.

    """

    component_config_schema = TokenUsageMessageCompletionConfig
    component_provider_override = "" #TODO

    def __init__(
        self,
        model_client: ChatCompletionClient,
        *,
        token_limit: int | None = None,
        tool_schema: List[ToolSchema] | None = None,
        internal_messages: List[LLMMessage] | None = None
    ) -> None:
        if token_limit is not None and token_limit <= 0:
            raise ValueError("token_limit must be greater than 0.")
        self._token_limit = token_limit
        self._total_token = 0
        self._model_client = model_client
        self._tool_schema = tool_schema or []
        if internal_messages is not None:
            self._internal_messages = internal_messages
        else:
            self._internal_messages = []

    @property
    def triggered(self) -> bool:
        _triggered = False
        if self._token_limit is None:
            if self._model_client.remaining_tokens(
                self._internal_messages,
                tools=self._tool_schema,
            ) < 0:
                _triggered = True
        else:
            if self._total_token >= self._token_limit:
                _triggered = True
        return _triggered

    async def __call__(self, messages: List[ContextMessage]) -> TriggerMessage | None:
        if self.triggered:
            raise MessageCompletionException("Triggered condition has already been reached")
        
        _messages = [m for m in messages if isinstance(m, LLMMessageInstance)]
        self._internal_messages.extend(_messages)
        
        self._total_token += self._model_client.count_tokens(_messages, tools=self._tool_schema)
        
        if self.triggered:
            content = f"Token usage limit reached, total token count: {self._total_token_count}, prompt token count: {self._prompt_token_count}, completion token count: {self._completion_token_count}."
            return TriggerMessage(content=content, source="TokenUsageMessageCompletion")
        return None

    async def reset(self) -> None:
        self._total_token = 0
        self._internal_messages = []

    def _to_config(self) -> TokenUsageMessageCompletionConfig:
        return TokenUsageMessageCompletionConfig(
            model_client=self._model_client.dump_component(),
            token_limit=self._token_limit,
            tool_schema=self._tool_schema,
            internal_messages=self._internal_messages,
        )

    @classmethod
    def _from_config(cls, config: TokenUsageMessageCompletionConfig) -> Self:
        return cls(
            model_client=ChatCompletionClient.load_component(config.model_client),
            token_limit=config.token_limit,
            tool_schema=config.tool_schema,
            internal_messages=config.internal_messages,
        )


if False: # TODO : Porting them
    class HandoffTerminationConfig(BaseModel):
        target: str


    class HandoffTermination(TerminationCondition, Component[HandoffTerminationConfig]):
        """Terminate the conversation if a :class:`~autogen_agentchat.messages.HandoffMessage`
        with the given target is received.

        Args:
            target (str): The target of the handoff message.
        """

        component_config_schema = HandoffTerminationConfig
        component_provider_override = "autogen_agentchat.conditions.HandoffTermination"

        def __init__(self, target: str) -> None:
            self._terminated = False
            self._target = target

        @property
        def terminated(self) -> bool:
            return self._terminated

        async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
            if self._terminated:
                raise TerminatedException("Termination condition has already been reached")
            for message in messages:
                if isinstance(message, HandoffMessage) and message.target == self._target:
                    self._terminated = True
                    return StopMessage(
                        content=f"Handoff to {self._target} from {message.source} detected.", source="HandoffTermination"
                    )
            return None

        async def reset(self) -> None:
            self._terminated = False

        def _to_config(self) -> HandoffTerminationConfig:
            return HandoffTerminationConfig(target=self._target)

        @classmethod
        def _from_config(cls, config: HandoffTerminationConfig) -> Self:
            return cls(target=config.target)


    class TimeoutTerminationConfig(BaseModel):
        timeout_seconds: float


    class TimeoutTermination(TerminationCondition, Component[TimeoutTerminationConfig]):
        """Terminate the conversation after a specified duration has passed.

        Args:
            timeout_seconds: The maximum duration in seconds before terminating the conversation.
        """

        component_config_schema = TimeoutTerminationConfig
        component_provider_override = "autogen_agentchat.conditions.TimeoutTermination"

        def __init__(self, timeout_seconds: float) -> None:
            self._timeout_seconds = timeout_seconds
            self._start_time = time.monotonic()
            self._terminated = False

        @property
        def terminated(self) -> bool:
            return self._terminated

        async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
            if self._terminated:
                raise TerminatedException("Termination condition has already been reached")

            if (time.monotonic() - self._start_time) >= self._timeout_seconds:
                self._terminated = True
                return StopMessage(
                    content=f"Timeout of {self._timeout_seconds} seconds reached", source="TimeoutTermination"
                )
            return None

        async def reset(self) -> None:
            self._start_time = time.monotonic()
            self._terminated = False

        def _to_config(self) -> TimeoutTerminationConfig:
            return TimeoutTerminationConfig(timeout_seconds=self._timeout_seconds)

        @classmethod
        def _from_config(cls, config: TimeoutTerminationConfig) -> Self:
            return cls(timeout_seconds=config.timeout_seconds)


    class ExternalTerminationConfig(BaseModel):
        pass


    class ExternalTermination(TerminationCondition, Component[ExternalTerminationConfig]):
        """A termination condition that is externally controlled
        by calling the :meth:`set` method.

        Example:

        .. code-block:: python

            from autogen_agentchat.conditions import ExternalTermination

            termination = ExternalTermination()

            # Run the team in an asyncio task.
            ...

            # Set the termination condition externally
            termination.set()

        """

        component_config_schema = ExternalTerminationConfig
        component_provider_override = "autogen_agentchat.conditions.ExternalTermination"

        def __init__(self) -> None:
            self._terminated = False
            self._setted = False

        @property
        def terminated(self) -> bool:
            return self._terminated

        def set(self) -> None:
            """Set the termination condition to terminated."""
            self._setted = True

        async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
            if self._terminated:
                raise TerminatedException("Termination condition has already been reached")
            if self._setted:
                self._terminated = True
                return StopMessage(content="External termination requested", source="ExternalTermination")
            return None

        async def reset(self) -> None:
            self._terminated = False
            self._setted = False

        def _to_config(self) -> ExternalTerminationConfig:
            return ExternalTerminationConfig()

        @classmethod
        def _from_config(cls, config: ExternalTerminationConfig) -> Self:
            return cls()


    class SourceMatchTerminationConfig(BaseModel):
        sources: List[str]


    class SourceMatchTermination(TerminationCondition, Component[SourceMatchTerminationConfig]):
        """Terminate the conversation after a specific source responds.

        Args:
            sources (List[str]): List of source names to terminate the conversation.

        Raises:
            TerminatedException: If the termination condition has already been reached.
        """

        component_config_schema = SourceMatchTerminationConfig
        component_provider_override = "autogen_agentchat.conditions.SourceMatchTermination"

        def __init__(self, sources: List[str]) -> None:
            self._sources = sources
            self._terminated = False

        @property
        def terminated(self) -> bool:
            return self._terminated

        async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
            if self._terminated:
                raise TerminatedException("Termination condition has already been reached")
            if not messages:
                return None
            for message in messages:
                if message.source in self._sources:
                    self._terminated = True
                    return StopMessage(content=f"'{message.source}' answered", source="SourceMatchTermination")
            return None

        async def reset(self) -> None:
            self._terminated = False

        def _to_config(self) -> SourceMatchTerminationConfig:
            return SourceMatchTerminationConfig(sources=self._sources)

        @classmethod
        def _from_config(cls, config: SourceMatchTerminationConfig) -> Self:
            return cls(sources=config.sources)


    class TextMessageTerminationConfig(BaseModel):
        """Configuration for the TextMessageTermination termination condition."""

        source: str | None = None
        """The source of the text message to terminate the conversation."""


    class TextMessageTermination(TerminationCondition, Component[TextMessageTerminationConfig]):
        """Terminate the conversation if a :class:`~autogen_agentchat.messages.TextMessage` is received.

        This termination condition checks for TextMessage instances in the message sequence. When a TextMessage is found,
        it terminates the conversation if either:
        - No source was specified (terminates on any TextMessage)
        - The message source matches the specified source

        Args:
            source (str | None, optional): The source name to match against incoming messages. If None, matches any source.
                Defaults to None.
        """

        component_config_schema = TextMessageTerminationConfig
        component_provider_override = "autogen_agentchat.conditions.TextMessageTermination"

        def __init__(self, source: str | None = None) -> None:
            self._terminated = False
            self._source = source

        @property
        def terminated(self) -> bool:
            return self._terminated

        async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
            if self._terminated:
                raise TerminatedException("Termination condition has already been reached")
            for message in messages:
                if isinstance(message, TextMessage) and (self._source is None or message.source == self._source):
                    self._terminated = True
                    return StopMessage(
                        content=f"Text message received from '{message.source}'", source="TextMessageTermination"
                    )
            return None

        async def reset(self) -> None:
            self._terminated = False

        def _to_config(self) -> TextMessageTerminationConfig:
            return TextMessageTerminationConfig(source=self._source)

        @classmethod
        def _from_config(cls, config: TextMessageTerminationConfig) -> Self:
            return cls(source=config.source)


    class FunctionCallTerminationConfig(BaseModel):
        """Configuration for the :class:`FunctionCallTermination` termination condition."""

        function_name: str


    class FunctionCallTermination(TerminationCondition, Component[FunctionCallTerminationConfig]):
        """Terminate the conversation if a :class:`~autogen_core.models.FunctionExecutionResult`
        with a specific name was received.

        Args:
            function_name (str): The name of the function to look for in the messages.

        Raises:
            TerminatedException: If the termination condition has already been reached.
        """

        component_config_schema = FunctionCallTerminationConfig
        """The schema for the component configuration."""

        def __init__(self, function_name: str) -> None:
            self._terminated = False
            self._function_name = function_name

        @property
        def terminated(self) -> bool:
            return self._terminated

        async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None:
            if self._terminated:
                raise TerminatedException("Termination condition has already been reached")
            for message in messages:
                if isinstance(message, ToolCallExecutionEvent):
                    for execution in message.content:
                        if execution.name == self._function_name:
                            self._terminated = True
                            return StopMessage(
                                content=f"Function '{self._function_name}' was executed.",
                                source="FunctionCallTermination",
                            )
            return None

        async def reset(self) -> None:
            self._terminated = False

        def _to_config(self) -> FunctionCallTerminationConfig:
            return FunctionCallTerminationConfig(
                function_name=self._function_name,
            )

        @classmethod
        def _from_config(cls, config: FunctionCallTerminationConfig) -> Self:
            return cls(
                function_name=config.function_name,
            )
        

