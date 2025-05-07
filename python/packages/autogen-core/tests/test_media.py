import pytest
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image as PILImage

from autogen_core import Media, Image, File
from autogen_core.models import UserMessage


def test_media_subclass_registration():
    """Test that Media subclasses are properly registered."""
    assert "Image" in Media._subclasses
    assert "File" in Media._subclasses
    assert Media._subclasses["Image"] == Image
    assert Media._subclasses["File"] == File


def test_image_as_media():
    """Test that Image can be used as Media."""
    # Create a simple image
    img = PILImage.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    base64_str = base64.b64encode(img_bytes).decode("utf-8")

    # Create an Image object
    image = Image.from_base64(base64_str)
    
    # Verify it's both an Image and a Media
    assert isinstance(image, Image)
    assert isinstance(image, Media)
    
    # Verify to_openai_format produces the expected structure
    openai_format = image.to_openai_format()
    assert openai_format["type"] == "image_url"
    assert "image_url" in openai_format
    assert "url" in openai_format["image_url"]
    assert openai_format["image_url"]["url"].startswith("data:image/png;base64,")


def test_file_as_media():
    """Test that File can be used as Media."""
    # Create a simple file
    file_content = b"This is a test file content"
    file_obj = File.from_bytes(file_content, "test.txt", "text/plain")
    
    # Verify it's both a File and a Media
    assert isinstance(file_obj, File)
    assert isinstance(file_obj, Media)
    
    # Verify to_openai_format produces the expected structure
    openai_format = file_obj.to_openai_format()
    assert openai_format["type"] == "file"
    assert "file" in openai_format
    assert "filename" in openai_format["file"]
    assert "file_data" in openai_format["file"]
    assert openai_format["file"]["filename"] == "test.txt"
    assert openai_format["file"]["file_data"].startswith("data:text/plain;base64,")


def test_user_message_with_media():
    """Test that UserMessage can contain different Media subclasses."""
    # Create an image
    img = PILImage.new("RGB", (100, 100), color="red")
    image = Image.from_pil(img)
    
    # Create a file
    file_content = b"This is a test file content"
    file_obj = File.from_bytes(file_content, "test.txt", "text/plain")
    
    # Create a UserMessage with both types of media
    message = UserMessage(
        content=["Here's an image and a file:", image, file_obj],
        source="user"
    )
    
    # Verify the message content has the correct types
    assert len(message.content) == 3
    assert isinstance(message.content[0], str)
    assert isinstance(message.content[1], Image)
    assert isinstance(message.content[2], File)
    assert isinstance(message.content[1], Media)
    assert isinstance(message.content[2], Media)


def test_media_subclass_cross_compatibility():
    """Test that different Media subclasses can be included in the same UserMessage."""
    # Create an image and a file
    img = PILImage.new("RGB", (100, 100), color="red")
    image = Image.from_pil(img)
    
    file_content = b"This is a test file content"
    file_obj = File.from_bytes(file_content, "test.txt", "text/plain")
    
    # Create a UserMessage with both media types
    message = UserMessage(
        content=["Here's the data:", image, file_obj],
        source="user"
    )
    
    # Check that the message contains both types correctly
    assert len(message.content) == 3
    assert isinstance(message.content[0], str)
    assert isinstance(message.content[1], Image)
    assert isinstance(message.content[2], File)
    assert isinstance(message.content[1], Media)
    assert isinstance(message.content[2], Media)
