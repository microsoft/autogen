import pytest

from autogen_core import Image
from autogen_core.models import UserMessage


def test_user_message_mixed_content_serialization() -> None:
    """
    Test that UserMessage can correctly serialize and deserialize
    mixed content containing both Image and string objects.
    Fixes Issue #7170.
    """
    # 1. Setup mixed content (Image + String)
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    img = Image.from_base64(test_image_b64)

    # 2. Construct the message
    original_msg = UserMessage(content=[img, "Identify this pixel."], source="user")

    # 3. Perform round-trip JSON serialization
    # This triggers the custom __get_pydantic_core_schema__ validator
    json_data = original_msg.model_dump_json()

    # 4. Attempt deserialization (The logic being tested)
    deserialized_msg = UserMessage.model_validate_json(json_data)

    # 5. Assertions
    assert isinstance(deserialized_msg.content, list)
    assert len(deserialized_msg.content) == 2
    assert isinstance(deserialized_msg.content[0], Image)
    assert isinstance(deserialized_msg.content[1], str)
    assert deserialized_msg.content[1] == "Identify this pixel."


if __name__ == "__main__":
    # Allow running directly for quick verification
    test_user_message_mixed_content_serialization()
    print("Regression test passed.")
