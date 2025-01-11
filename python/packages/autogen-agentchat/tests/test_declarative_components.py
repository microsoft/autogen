import pytest
from autogen_agentchat.base import OrTerminationCondition
from autogen_agentchat.conditions import MaxMessageTermination, StopMessageTermination
from autogen_agentchat.messages import StopMessage
from autogen_core import ComponentLoader, ComponentModel


@pytest.mark.asyncio
async def test_termination_declarative() -> None:
    """Test that termination conditions can be declared and serialized properly."""
    # Create basic termination conditions
    max_term = MaxMessageTermination(5)
    stop_term = StopMessageTermination()

    # Test basic serialization
    max_config = max_term.dump_component()
    assert isinstance(max_config, ComponentModel)
    assert max_config.provider == "autogen_agentchat.conditions.MaxMessageTermination"
    assert max_config.config.get("max_messages") == 5

    # Test basic deserialization
    loaded_max = ComponentLoader.load_component(max_config, MaxMessageTermination)
    assert isinstance(loaded_max, MaxMessageTermination)
    # Use public interface to verify state
    messages = [StopMessage(content="msg", source="test") for _ in range(5)]
    result = await loaded_max(messages)
    assert isinstance(result, StopMessage)

    # Test composition and complex serialization
    or_term = max_term | stop_term
    or_config = or_term.dump_component()
    assert or_config.provider == "autogen_agentchat.base.OrTerminationCondition"
    assert len(or_config.config["conditions"]) == 2

    # Verify nested conditions are correctly serialized
    conditions = or_config.config["conditions"]
    assert conditions[0]["provider"] == "autogen_agentchat.conditions.MaxMessageTermination"
    assert conditions[1]["provider"] == "autogen_agentchat.conditions.StopMessageTermination"

    # Test behavior of loaded composite condition
    loaded_or = OrTerminationCondition.load_component(or_config)

    # Test with stop message
    stop_messages = [StopMessage(content="stop", source="test")]
    result = await loaded_or(stop_messages)
    assert isinstance(result, StopMessage)
    assert loaded_or.terminated

    # Test reset functionality
    await loaded_or.reset()
    assert not loaded_or.terminated
