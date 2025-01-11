import pytest
from autogen_agentchat.conditions import StopMessageTermination, MaxMessageTermination
from autogen_agentchat.messages import StopMessage, TextMessage
from autogen_core import ComponentLoader


@pytest.mark.asyncio
async def test_termination_declarative() -> None:
    """Test that termination conditions can be declared and serialized properly."""
    # Create basic termination conditions
    max_term = MaxMessageTermination(5)
    stop_term = StopMessageTermination()

    # Test basic serialization/deserialization
    max_config = max_term.dump_component()
    assert max_config.provider == "autogen_agentchat.conditions.MaxMessageTermination"
    assert max_config.config["max_messages"] == 5
    loaded_max = ComponentLoader.load_component(max_config)
    assert isinstance(loaded_max, MaxMessageTermination)
    assert loaded_max._max_messages == 5

    # Test composition and complex serialization
    or_term = max_term | stop_term
    or_config = or_term.dump_component()
    assert or_config.provider == "autogen_agentchat.base.OrTerminationCondition"
    assert len(or_config.config["conditions"]) == 2

    # Test behavior after deserialization
    loaded_or = ComponentLoader.load_component(or_config)
    messages = [StopMessage(content="stop", source="test")]
    result = await loaded_or(messages)
    assert isinstance(result, StopMessage)
    await loaded_or.reset()
    assert not loaded_or.terminated
