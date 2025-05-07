"""Tests specifically for File class integration with OpenAI."""

import base64
import pytest
from autogen_core import File
from autogen_core.models import UserMessage

def test_file_openai_format():
    """Test that the File class produces the correct OpenAI format."""
    sample_content = b"Test PDF content"
    filename = "test_doc.pdf"
    mime_type = "application/pdf"
    
    # Create a File instance
    file = File.from_bytes(sample_content, filename, mime_type)
    
    # Get the OpenAI format
    openai_format = file.to_openai_format()
    
    # Check the structure
    assert isinstance(openai_format, dict)
    assert openai_format["type"] == "file"
    assert "file" in openai_format
    assert "filename" in openai_format["file"]
    assert "file_data" in openai_format["file"]
    
    # Check the values
    assert openai_format["file"]["filename"] == filename
    
    # Check the data URI structure
    data_uri = openai_format["file"]["file_data"]
    assert data_uri.startswith(f"data:{mime_type};base64,")
    
    # Decode the base64 part from the data URI
    base64_data = data_uri.replace(f"data:{mime_type};base64,", "")
    decoded_data = base64.b64decode(base64_data)
    
    # Verify the content
    assert decoded_data == sample_content

def test_file_in_user_message_list():
    """Test using a File object in a UserMessage with mixed content types."""
    text = "Please analyze this document:"
    sample_content = b"Test PDF content"
    filename = "test_doc.pdf"
    mime_type = "application/pdf"
    
    # Create a File instance
    file = File.from_bytes(sample_content, filename, mime_type)
    
    # Create a UserMessage with mixed content
    message = UserMessage(
        content=[text, file],
        source="user"
    )
    
    # Verify message structure
    assert isinstance(message.content, list)
    assert len(message.content) == 2
    assert message.content[0] == text
    assert message.content[1] == file
    
    # Get the OpenAI-formatted content
    # This would be called by the OpenAI client when sending the message
    file_in_content = message.content[1]
    openai_format = file_in_content.to_openai_format()
    
    # Verify format
    assert openai_format["type"] == "file"
    assert openai_format["file"]["filename"] == filename
