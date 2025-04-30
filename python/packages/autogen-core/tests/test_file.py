import base64
import os
import pytest
from pathlib import Path
from autogen_core import File
from autogen_core.models import UserMessage


def test_file_from_file():
    """Test creating a File object from a file path."""
    sample_content = b"This is a sample PDF file content"
    file_path = create_temp_file(sample_content)
    
    try:
        file = File.from_file(file_path)
        assert file.data == sample_content  # Note the attribute is 'data', not 'content'
        assert file.mime_type == "application/pdf"  # Should detect from file extension
        assert file.filename == file_path.name
    finally:
        # Clean up
        os.unlink(file_path)


def test_file_from_bytes():
    """Test creating a File object from bytes."""
    sample_content = b"This is a sample PDF file content"
    filename = "test.pdf"
    file = File.from_bytes(sample_content, filename, "application/pdf")
    
    # Test basic attributes
    assert file.data == sample_content
    assert file.mime_type == "application/pdf"
    assert file.filename == filename
    
    # Test base64 conversion
    base64_str = file.to_base64()
    decoded = base64.b64decode(base64_str)
    assert decoded == sample_content


def test_file_from_base64():
    """Test creating a File object from base64 string."""
    sample_content = b"This is a sample PDF file content"
    base64_str = base64.b64encode(sample_content).decode("utf-8")
    filename = "test.pdf"
    
    file = File.from_base64(base64_str, filename, "application/pdf")
    assert file.data == sample_content
    assert file.mime_type == "application/pdf"
    assert file.filename == filename


def create_temp_file(content, suffix=".pdf"):
    """Create a temporary file for testing."""
    import tempfile
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(content)
        return Path(f.name)


def test_file_to_data_uri():
    """Test the to_data_uri method."""
    sample_content = b"This is a sample PDF file content"
    filename = "test.pdf"
    mime_type = "application/pdf"
    file = File.from_bytes(sample_content, filename, mime_type)
    
    expected_uri = f"data:{mime_type};base64,{base64.b64encode(sample_content).decode('utf-8')}"
    assert file.to_data_uri() == expected_uri


def test_file_to_openai_format():
    """Test the to_openai_format method."""
    sample_content = b"This is a sample PDF file content"
    filename = "test.pdf"
    mime_type = "application/pdf"
    file = File.from_bytes(sample_content, filename, mime_type)
    
    openai_format = file.to_openai_format()
    assert openai_format["type"] == "file"
    assert "file" in openai_format
    assert "filename" in openai_format["file"]
    assert openai_format["file"]["filename"] == filename
    assert "file_data" in openai_format["file"]
    # Check that file_data contains the data_uri
    assert file.to_data_uri() == openai_format["file"]["file_data"]


def test_file_in_user_message():
    """Test using a File object in a UserMessage."""
    sample_content = b"This is a sample PDF file content"
    filename = "test.pdf" 
    file = File.from_bytes(sample_content, filename, "application/pdf")
    
    # Test with a mixed content (text and file)
    message = UserMessage(
        content=["Please analyze this file:", file],
        source="user"
    )
    
    assert isinstance(message.content, list)
    assert len(message.content) == 2
    assert message.content[0] == "Please analyze this file:"
    assert message.content[1] == file or message.content[1] is file
