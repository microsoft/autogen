from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from typing import Any, Dict, Optional, cast

from pydantic import GetCoreSchemaHandler, ValidationInfo
from pydantic_core import core_schema
from typing_extensions import Literal

from ._media import Media


class File(Media):
    """Represents a file that can be sent to an LLM.

    This class is designed to handle file attachments in messages to language models
    that support file inputs, such as GPT-4 Vision or GPT-4.1. It supports various file
    formats including PDF, text files, and any other file type.

    Example:

        Loading a file from disk:

        .. code-block:: python

            from autogen_core import File

            # Load a PDF file
            pdf_file = File.from_file(Path("document.pdf"))

            # Use in a message
            message = UserMessage(
                content=["Please analyze this document", pdf_file],
                source="user"
            )

        Creating a File from bytes:

        .. code-block:: python

            # From raw bytes
            file_content = b"Document content"
            file_obj = File.from_bytes(file_content, "document.txt", "text/plain")

        Creating a File from base64:

        .. code-block:: python

            # From base64 string (e.g., when receiving data from an API)
            base64_content = "VGVzdCBjb250ZW50"  # "Test content" in base64
            file_obj = File.from_base64(base64_content, "document.txt")
    """

    media_type = "file"

    def __init__(self, filename: str, data: bytes, mime_type: Optional[str] = None):
        """Initialize a File object.
        
        Args:
            filename: The name of the file
            data: The file content as bytes
            mime_type: The MIME type of the file (guessed from filename if not provided)
        """
        self.filename = filename
        self.data = data
        self.mime_type = mime_type or self._guess_mime_type(filename)

    @staticmethod
    def _guess_mime_type(filename: str) -> str:
        """Guess the MIME type from the filename."""
        guessed_type = mimetypes.guess_type(filename)[0]
        return guessed_type or "application/octet-stream"

    @classmethod
    def from_file(cls, file_path: Path) -> File:
        """Create a File object from a file path."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return cls(
            filename=file_path.name,
            data=file_path.read_bytes(),
            mime_type=mimetypes.guess_type(file_path.name)[0]
        )

    @classmethod
    def from_bytes(cls, data: bytes, filename: str, mime_type: Optional[str] = None) -> File:
        """Create a File object from bytes."""
        return cls(
            filename=filename,
            data=data,
            mime_type=mime_type
        )

    @classmethod
    def from_base64(cls, base64_str: str, filename: str, mime_type: Optional[str] = None) -> File:
        """Create a File object from a base64 encoded string."""
        data = base64.b64decode(base64_str)
        return cls(
            filename=filename,
            data=data,
            mime_type=mime_type
        )

    @classmethod
    def from_data_uri(cls, uri: str, filename: str) -> File:
        """Create a File object from a data URI."""
        if not re.match(r"data:[^;]+;base64,", uri):
            raise ValueError("Invalid URI format. It should be a base64 encoded data URI.")

        mime_type = cls._get_mime_type_from_data_uri(uri)
        if not mime_type:
            raise ValueError("Could not extract MIME type from data URI")

        base64_data = cls._extract_base64_from_data_uri(uri)
        return cls.from_base64(base64_data, filename, mime_type)

    def to_base64(self) -> str:
        """Convert the file data to a base64 encoded string."""
        return base64.b64encode(self.data).decode("utf-8")

    def to_data_uri(self) -> str:
        """Convert the file to a data URI."""
        base64_str = self.to_base64()
        return f"data:{self.mime_type};base64,{base64_str}"

    # Returns a format suitable for OpenAI API (based on official example for gpt-4.1/gpt-4o)
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert the file to the format expected by OpenAI API for direct inclusion in content."""
        return {
            "type": "file",
            "file": {
                "filename": self.filename,
                "file_data": self.to_data_uri(),
            }
        }

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Pydantic validation schema with passthrough for other Media types."""
        
        # Custom validation specific to File
        def validate(value: Any, validation_info: ValidationInfo) -> Any:
            # Check if value is another Media subclass first (allow passthrough)
            for subclass_name, subclass in Media._subclasses.items():
                if subclass_name != "File" and isinstance(value, subclass):
                    return value
            
            # Now handle File-specific cases
            if isinstance(value, dict):
                filename = cast(str | None, value.get("filename"))
                data = cast(str | None, value.get("data"))  # Expecting base64 data
                mime_type = cast(str | None, value.get("mime_type"))

                if filename is None or data is None:
                    raise ValueError("Expected 'filename' and 'data' (base64 encoded) keys in the dictionary")

                try:
                    return cls.from_base64(data, filename, mime_type)
                except Exception as e:
                    raise ValueError(f"Invalid base64 file data: {e}")
            elif isinstance(value, cls):
                return value
            else:
                raise TypeError(f"Expected dict, {cls.__name__} instance, or another Media type, got {type(value)}")

        # Custom serialization
        def serialize(value: Any) -> Any:
            if isinstance(value, File):
                return {
                    "filename": value.filename,
                    "data": value.to_base64(),
                    "mime_type": value.mime_type
                }
            # For other Media types, let their own serializers handle it
            return value

        return core_schema.with_info_after_validator_function(
            validate,
            core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize, when_used='unless-none'),
        )
        
    def __repr__(self) -> str:
        """String representation of the File object."""
        return f"File(filename='{self.filename}', mime_type='{self.mime_type}', size={len(self.data)} bytes)"
