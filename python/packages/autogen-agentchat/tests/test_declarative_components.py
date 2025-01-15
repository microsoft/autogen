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
from autogen_core import ComponentLoader, ComponentModel, CancellationToken
from autogen_core.tools import FunctionTool
from autogen_core.code_executor import ImportFromModule


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
async def test_function_tool() -> None:
    """Test FunctionTool with different function types and features."""

    # Test sync and async functions
    def sync_func(x: int, y: str) -> str:
        return y * x

    async def async_func(x: float, y: float, cancellation_token: CancellationToken) -> float:
        if cancellation_token.is_cancelled():
            raise Exception("Cancelled")
        return x + y

    # Create tools with different configurations
    sync_tool = FunctionTool(
        func=sync_func, description="Multiply string", global_imports=[ImportFromModule("typing", ("Dict",))]
    )
    async_tool = FunctionTool(
        func=async_func,
        description="Add numbers",
        name="custom_adder",
        global_imports=[ImportFromModule("autogen_core", ("CancellationToken",))],
    )

    # Test serialization and config

    sync_config = sync_tool.dump_component()
    assert isinstance(sync_config, ComponentModel)
    assert sync_config.config["name"] == "sync_func"
    assert len(sync_config.config["global_imports"]) == 1
    assert not sync_config.config["has_cancellation_support"]

    async_config = async_tool.dump_component()
    assert async_config.config["name"] == "custom_adder"
    assert async_config.config["has_cancellation_support"]

    # Test deserialization and execution
    loaded_sync = FunctionTool.load_component(sync_config, FunctionTool)
    loaded_async = FunctionTool.load_component(async_config, FunctionTool)

    # Test execution and validation
    token = CancellationToken()
    assert await loaded_sync.run_json({"x": 2, "y": "test"}, token) == "testtest"
    assert await loaded_async.run_json({"x": 1.5, "y": 2.5}, token) == 4.0

    # Test error cases
    with pytest.raises(ValueError):
        # Type error
        await loaded_sync.run_json({"x": "invalid", "y": "test"}, token)

    cancelled_token = CancellationToken()
    cancelled_token.cancel()
    with pytest.raises(Exception, match="Cancelled"):
        await loaded_async.run_json({"x": 1.0, "y": 2.0}, cancelled_token)
