"""Test for issue #7170 - UserMessage with mixed string and Image content deserialization."""

import pytest
from autogen_core import Image
from autogen_core.models import UserMessage


class TestImageMixedContentDeserialization:
    """Tests for UserMessage with mixed string and Image content."""

    def test_user_message_with_string_only(self) -> None:
        """Test UserMessage with string content serialization/deserialization."""
        msg = UserMessage(content="Hello world", source="user")
        json_str = msg.model_dump_json()
        restored = UserMessage.model_validate_json(json_str)
        assert restored.content == "Hello world"
        assert restored.source == "user"

    def test_user_message_with_image_only(self) -> None:
        """Test UserMessage with Image only in list."""
        # Create a small test image (1x1 red pixel PNG)
        import base64
        from io import BytesIO
        from PIL import Image as PILImage

        # Create a 1x1 red image
        pil_img = PILImage.new("RGB", (1, 1), color="red")
        buffered = BytesIO()
        pil_img.save(buffered, format="PNG")
        base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        img = Image.from_base64(base64_str)
        msg = UserMessage(content=[img], source="user")
        json_str = msg.model_dump_json()
        restored = UserMessage.model_validate_json(json_str)

        assert isinstance(restored.content, list)
        assert len(restored.content) == 1
        assert isinstance(restored.content[0], Image)

    def test_user_message_with_mixed_content(self) -> None:
        """Test UserMessage with both string and Image content - issue #7170."""
        import base64
        from io import BytesIO
        from PIL import Image as PILImage

        # Create a 1x1 red image
        pil_img = PILImage.new("RGB", (1, 1), color="red")
        buffered = BytesIO()
        pil_img.save(buffered, format="PNG")
        base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        img = Image.from_base64(base64_str)

        # This is the exact case from issue #7170
        msg = UserMessage(content=[img, "Please describe this image"], source="user")
        json_str = msg.model_dump_json()

        # This was failing before the fix with:
        # "Expected dict or Image instance, got <class 'str'>"
        restored = UserMessage.model_validate_json(json_str)

        assert isinstance(restored.content, list)
        assert len(restored.content) == 2
        assert isinstance(restored.content[0], Image)
        assert restored.content[1] == "Please describe this image"

    def test_user_message_with_string_first_then_image(self) -> None:
        """Test UserMessage with string before Image in list."""
        import base64
        from io import BytesIO
        from PIL import Image as PILImage

        # Create a 1x1 blue image
        pil_img = PILImage.new("RGB", (1, 1), color="blue")
        buffered = BytesIO()
        pil_img.save(buffered, format="PNG")
        base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        img = Image.from_base64(base64_str)
        msg = UserMessage(content=["What is in this image?", img], source="user")
        json_str = msg.model_dump_json()
        restored = UserMessage.model_validate_json(json_str)

        assert isinstance(restored.content, list)
        assert len(restored.content) == 2
        assert restored.content[0] == "What is in this image?"
        assert isinstance(restored.content[1], Image)

    def test_user_message_with_multiple_strings_and_images(self) -> None:
        """Test UserMessage with multiple strings and images."""
        import base64
        from io import BytesIO
        from PIL import Image as PILImage

        # Create two different images
        pil_img1 = PILImage.new("RGB", (1, 1), color="red")
        buffered1 = BytesIO()
        pil_img1.save(buffered1, format="PNG")
        img1 = Image.from_base64(base64.b64encode(buffered1.getvalue()).decode("utf-8"))

        pil_img2 = PILImage.new("RGB", (1, 1), color="green")
        buffered2 = BytesIO()
        pil_img2.save(buffered2, format="PNG")
        img2 = Image.from_base64(base64.b64encode(buffered2.getvalue()).decode("utf-8"))

        msg = UserMessage(
            content=["First text", img1, "Second text", img2, "Third text"],
            source="user"
        )
        json_str = msg.model_dump_json()
        restored = UserMessage.model_validate_json(json_str)

        assert isinstance(restored.content, list)
        assert len(restored.content) == 5
        assert restored.content[0] == "First text"
        assert isinstance(restored.content[1], Image)
        assert restored.content[2] == "Second text"
        assert isinstance(restored.content[3], Image)
        assert restored.content[4] == "Third text"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
