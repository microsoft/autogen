import pytest
from autogen_agentchat.base import AndTerminationCondition
from autogen_agentchat.conditions import (
    ExternalTermination,
    HandoffTermination,
    MaxMessageTermination,
    SourceMatchTermination,
    StopMessageTermination,
    TextMentionTermination,
    TimeoutTermination,
    TokenUsageTermination,
)
from autogen_core import ComponentLoader, ComponentModel
from autogen_core.model_context import (
    BufferedChatCompletionContext,
    HeadAndTailChatCompletionContext,
    UnboundedChatCompletionContext,
    TokenLimitedChatCompletionContext,
)


@pytest.mark.asyncio
async def test_termination_declarative() -> None:
    """Test that termination conditions can be declared and serialized properly."""
    # Create basic termination conditions
    max_term = MaxMessageTermination(5)
    stop_term = StopMessageTermination()
    text_term = TextMentionTermination("stop")
    token_term = TokenUsageTermination(max_total_token=100, max_prompt_token=50, max_completion_token=100)
    handoff_term = HandoffTermination(target="human")
    timeout_term = TimeoutTermination(timeout_seconds=30)
    external_term = ExternalTermination()
    source_term = SourceMatchTermination(sources=["human"])

    # Test basic serialization
    max_config = max_term.dump_component()
    assert isinstance(max_config, ComponentModel)
    assert max_config.provider == "autogen_agentchat.conditions.MaxMessageTermination"
    assert max_config.config.get("max_messages") == 5

    # Test serialization of new conditions
    text_config = text_term.dump_component()
    assert text_config.provider == "autogen_agentchat.conditions.TextMentionTermination"
    assert text_config.config.get("text") == "stop"

    token_config = token_term.dump_component()
    assert token_config.provider == "autogen_agentchat.conditions.TokenUsageTermination"
    assert token_config.config.get("max_total_token") == 100

    handoff_config = handoff_term.dump_component()
    assert handoff_config.provider == "autogen_agentchat.conditions.HandoffTermination"
    assert handoff_config.config.get("target") == "human"

    timeout_config = timeout_term.dump_component()
    assert timeout_config.provider == "autogen_agentchat.conditions.TimeoutTermination"
    assert timeout_config.config.get("timeout_seconds") == 30

    external_config = external_term.dump_component()
    assert external_config.provider == "autogen_agentchat.conditions.ExternalTermination"

    source_config = source_term.dump_component()
    assert source_config.provider == "autogen_agentchat.conditions.SourceMatchTermination"
    assert source_config.config.get("sources") == ["human"]

    # Test basic deserialization
    loaded_max = ComponentLoader.load_component(max_config, MaxMessageTermination)
    assert isinstance(loaded_max, MaxMessageTermination)

    # Test deserialization of new conditions
    loaded_text = ComponentLoader.load_component(text_config, TextMentionTermination)
    assert isinstance(loaded_text, TextMentionTermination)

    loaded_token = ComponentLoader.load_component(token_config, TokenUsageTermination)
    assert isinstance(loaded_token, TokenUsageTermination)

    loaded_handoff = ComponentLoader.load_component(handoff_config, HandoffTermination)
    assert isinstance(loaded_handoff, HandoffTermination)

    loaded_timeout = ComponentLoader.load_component(timeout_config, TimeoutTermination)
    assert isinstance(loaded_timeout, TimeoutTermination)

    loaded_external = ComponentLoader.load_component(external_config, ExternalTermination)
    assert isinstance(loaded_external, ExternalTermination)

    loaded_source = ComponentLoader.load_component(source_config, SourceMatchTermination)
    assert isinstance(loaded_source, SourceMatchTermination)

    # Test composition with new conditions
    composite_term = (max_term | stop_term) & (token_term | handoff_term)
    composite_config = composite_term.dump_component()

    assert composite_config.provider == "autogen_agentchat.base.AndTerminationCondition"
    conditions = composite_config.config["conditions"]
    assert len(conditions) == 2
    assert conditions[0]["provider"] == "autogen_agentchat.base.OrTerminationCondition"
    assert conditions[1]["provider"] == "autogen_agentchat.base.OrTerminationCondition"

    # Test loading complex composition
    loaded_composite = ComponentLoader.load_component(composite_config)
    assert isinstance(loaded_composite, AndTerminationCondition)


@pytest.mark.asyncio
async def test_chat_completion_context_declarative() -> None:
    unbounded_context = UnboundedChatCompletionContext()
    buffered_context = BufferedChatCompletionContext(buffer_size=5)
    head_tail_context = HeadAndTailChatCompletionContext(head_size=3, tail_size=2)
    token_limited_context = TokenLimitedChatCompletionContext(token_limit=5, model="gpt-4o")

    # Test serialization
    unbounded_config = unbounded_context.dump_component()
    assert unbounded_config.provider == "autogen_core.model_context.UnboundedChatCompletionContext"

    buffered_config = buffered_context.dump_component()
    assert buffered_config.provider == "autogen_core.model_context.BufferedChatCompletionContext"
    assert buffered_config.config["buffer_size"] == 5

    head_tail_config = head_tail_context.dump_component()
    assert head_tail_config.provider == "autogen_core.model_context.HeadAndTailChatCompletionContext"
    assert head_tail_config.config["head_size"] == 3
    assert head_tail_config.config["tail_size"] == 2

    token_limited_config = token_limited_context.dump_component()
    assert token_limited_config.provider == "autogen_core.model_context.TokenLimitedChatCompletionContext"
    assert token_limited_config.config["token_limit"] == 5
    assert token_limited_config.config["model"] == "gpt-4o"

    # Test deserialization
    loaded_unbounded = ComponentLoader.load_component(unbounded_config, UnboundedChatCompletionContext)
    assert isinstance(loaded_unbounded, UnboundedChatCompletionContext)

    loaded_buffered = ComponentLoader.load_component(buffered_config, BufferedChatCompletionContext)

    assert isinstance(loaded_buffered, BufferedChatCompletionContext)

    loaded_head_tail = ComponentLoader.load_component(head_tail_config, HeadAndTailChatCompletionContext)

    assert isinstance(loaded_head_tail, HeadAndTailChatCompletionContext)

    loaded_token_limited = ComponentLoader.load_component(token_limited_config, TokenLimitedChatCompletionContext)
    assert isinstance(loaded_token_limited, TokenLimitedChatCompletionContext)
