from __future__ import annotations

import base64
import mimetypes
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, cast

from pydantic import GetCoreSchemaHandler, ValidationInfo
from pydantic_core import core_schema, ValidationError
from typing_extensions import Literal


class File:
    """Represents a file that can be sent to models.

    This class provides methods to create File objects from different sources and convert them to
    formats required by different API providers.

    Example:

        Loading a file from a path:

        .. code-block:: python

            from autogen_core import File

            # Create from file path
            file = File.from_path("document.pdf")

            # Create from file ID (if already uploaded to OpenAI)
            file = File.from_file_id("file-abc123")

            # Create from base64 content
            file = File.from_base64(base64_content, filename="document.pdf")
    """

    def __init__(
        self, 
        file_content: bytes = None, 
        filename: str = None, 
        mime_type: str = None, 
        file_id: str = None
    ):
        self.file_content = file_content
        self.filename = filename
        self.mime_type = mime_type
        self.file_id = file_id

        # Try to determine mime_type from filename if not provided
        if self.filename and not self.mime_type:
            self.mime_type = mimetypes.guess_type(self.filename)[0] or "application/octet-stream"

    @classmethod
    def from_path(cls, file_path: str | Path) -> File:
        """Create a File object from a file path.

        Args:
            file_path: Path to the file.

        Returns:
            File: A new File instance.
        """
        path = Path(file_path) if isinstance(file_path, str) else file_path
        with open(path, "rb") as f:
            file_content = f.read()
        
        return cls(
            file_content=file_content,
            filename=path.name,
            mime_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        )

    @classmethod
    def from_file_id(cls, file_id: str, filename: str = None) -> File:
        """Create a File object from an OpenAI file ID.

        Args:
            file_id: The file ID from OpenAI API.
            filename: Optional filename to associate with this file.

        Returns:
            File: A new File instance referencing an existing uploaded file.
        """
        return cls(file_id=file_id, filename=filename)

    @classmethod
    def from_base64(cls, base64_str: str, filename: str = None, mime_type: str = None) -> File:
        """Create a File object from a base64 encoded string.

        Args:
            base64_str: Base64 encoded file content.
            filename: Filename to use for the file.
            mime_type: MIME type of the file.

        Returns:
            File: A new File instance.
        """
        file_content = base64.b64decode(base64_str)
        return cls(file_content=file_content, filename=filename, mime_type=mime_type)

    def to_base64(self) -> str:
        """Convert file content to base64 encoded string.

        Returns:
            str: Base64 encoded file content.
        """
        if not self.file_content:
            raise ValueError("File content is not available. Use a file created from path or base64.")
        
        return base64.b64encode(self.file_content).decode("utf-8")

    def to_data_url(self) -> str:
        """Convert file content to a data URL string.

        Returns:
            str: Data URL string.
        """
        if not self.file_content:
            raise ValueError("File content is not available to create a data URL.")
        if not self.mime_type:
            if self.filename:
                # Try to guess MIME type if filename is available but mime_type wasn't set during init
                guessed_mime_type = mimetypes.guess_type(self.filename)[0]
                if guessed_mime_type:
                    self.mime_type = guessed_mime_type
                else:
                    # Fallback if guess fails, though application/octet-stream is a common default
                    raise ValueError("MIME type could not be guessed from filename and is required for data URL.")
            else:
                raise ValueError("MIME type is required to create a data URL, and filename is not available to guess.")
        
        base64_content = self.to_base64() # Uses the existing method
        return f"data:{self.mime_type};base64,{base64_content}"

    def to_openai_format(self, use_file_id: bool = False) -> Dict[str, Any]:
        """Convert the file to OpenAI API format.

        Args:
            use_file_id: If True and file_id is available, use file_id reference.
                         Otherwise use base64 content.

        Returns:
            Dict[str, Any]: OpenAI compatible file format dictionary.
        """
        if use_file_id and self.file_id:
            return {
                "type": "file",
                "file": {
                    "file_id": self.file_id
                }
            }
        elif self.file_content:
            if not self.filename:
                raise ValueError("Filename must be provided when using file content")
            
            return {
                "type": "file",
                "file": {
                    "filename": self.filename,
                    "file_data": self.to_data_url()
                }
            }
        else:
            raise ValueError("Either file_id or file_content must be available")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        # Custom validation
        def validate(value: Any, validation_info: ValidationInfo) -> File:
            if isinstance(value, dict):
                if "file_id" in value:
                    return cls.from_file_id(value["file_id"], value.get("filename"))
                elif "data" in value:
                    return cls.from_base64(
                        value["data"], 
                        value.get("filename"), 
                        value.get("mime_type")
                    )
                elif "path" in value:
                    return cls.from_path(value["path"])
                else:
                    # This ValueError is for specific dict structures, which is fine.
                    raise ValueError("Expected 'file_id', 'data', or 'path' key in the dictionary")
            elif isinstance(value, cls):
                return value
            elif isinstance(value, (str, Path)):
                # Assume it's a file path
                return cls.from_path(value)
            else:
                # Instead of raising TypeError, raise pydantic_core.ValidationError
                raise ValidationError.from_exception_data(
                    title=cls.__name__,
                    line_errors=[
                        {
                            "type": "model_type",
                            "loc": ("File",),
                            "input": value,
                            "ctx": {"class_name": cls.__name__},
                        }
                    ],
                )

        # Custom serialization
        def serialize(value: File) -> dict[str, Any]:
            if value.file_id:
                result = {"file_id": value.file_id}
                return result
            elif value.file_content:
                result = {"file_data": value.to_data_url()}
                if value.filename:
                    result["filename"] = value.filename
                return result
            else:
                raise ValueError("File has no content or file_id")

        return core_schema.with_info_after_validator_function(
            validate,
            core_schema.any_schema(),  # Accept any type; adjust if needed
            serialization=core_schema.plain_serializer_function_ser_schema(serialize),
        )

