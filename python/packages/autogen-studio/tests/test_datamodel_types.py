import pytest

from autogenstudio.datamodel.types import LLMCallEventMessage

def test_LLMCallEventMessage_inner_funcs():
    """Test the inner functions of LLMCallEventMessage"""
    # Create a mock LLMCallEventMessage
    message = LLMCallEventMessage(
        content="Test message"
    )

    # Test the inner functions
    assert message.to_text() == "Test message"
    assert message.to_model_text() == "Test message"
    with pytest.raises(NotImplementedError, match="This message type is not supported."):
        message.to_model_message()