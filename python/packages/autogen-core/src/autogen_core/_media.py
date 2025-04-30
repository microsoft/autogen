from __future__ import annotations

import base64
import mimetypes
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, cast, ClassVar

from pydantic import GetCoreSchemaHandler, ValidationInfo
from pydantic_core import core_schema

# Define a TypeVar for returning subclass instances from class methods
T = TypeVar('T', bound='Media')

class Media:
    """Base class for media objects (images, files, etc.) that can be sent to an LLM.
    
    This class provides common functionality for different media types, including:
    - Base64 encoding/decoding
    - Data URI conversion
    - Serialization for OpenAI API format
    
    Subclasses should implement:
    - __init__ method with appropriate attributes
    - to_openai_format() method returning the specific format for the API
    - From_* factory methods where appropriate
    - Media-specific processing
    """
    
    # Class-level registry for subclass validation lookups
    _subclasses: ClassVar[Dict[str, type]] = {}
    
    # Media type identifier (to be defined by subclasses)
    media_type: str = "generic"
    
    def __init_subclass__(cls, **kwargs):
        """Register subclasses for validation purposes"""
        super().__init_subclass__(**kwargs)
        Media._subclasses[cls.__name__] = cls
    
    def to_base64(self) -> str:
        """Convert the media data to a base64 encoded string."""
        raise NotImplementedError("Subclasses must implement to_base64()")
    
    def to_data_uri(self) -> str:
        """Convert the media to a data URI."""
        raise NotImplementedError("Subclasses must implement to_data_uri()")
    
    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to the format expected by OpenAI API."""
        raise NotImplementedError("Subclasses must implement to_openai_format()")
    
    @classmethod
    def from_base64(cls: type[T], base64_str: str, **kwargs) -> T:
        """Create a media object from a base64 encoded string."""
        raise NotImplementedError("Subclasses must implement from_base64()")
    
    @classmethod
    def from_file(cls: type[T], file_path: Path, **kwargs) -> T:
        """Create a media object from a file path."""
        raise NotImplementedError("Subclasses must implement from_file()")
    
    @classmethod
    def from_data_uri(cls: type[T], uri: str, **kwargs) -> T:
        """Create a media object from a data URI."""
        raise NotImplementedError("Subclasses must implement from_data_uri()")
    
    @staticmethod
    def _get_mime_type_from_data_uri(uri: str) -> Optional[str]:
        """Extract MIME type from a data URI."""
        mime_match = re.match(r"data:([^;]+);base64,", uri)
        if not mime_match:
            return None
        return mime_match.group(1)
    
    @staticmethod
    def _extract_base64_from_data_uri(uri: str) -> str:
        """Extract base64 data from a data URI."""
        if not re.match(r"data:[^;]+;base64,", uri):
            raise ValueError("Invalid URI format. It should be a base64 encoded data URI.")
        return re.sub(r"data:[^;]+;base64,", "", uri)
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Pydantic validation schema for Media subclasses.
        
        This base implementation defines the common validation logic that allows instances
        of any Media subclass to pass through validation when in the context of a list.
        
        Subclasses should override with their specific validation logic while maintaining
        the pass-through behavior for other Media types.
        """
        
        # Custom validation
        def validate(value: Any, validation_info: ValidationInfo) -> Any:
            # Allow any Media subclass to pass through validation
            for subclass in Media._subclasses.values():
                if isinstance(value, subclass):
                    return value
            
            # Default rejection for other types
            raise TypeError(f"Expected a Media subclass instance, got {type(value)}")
            
        # Custom serialization - let subclasses handle
        def serialize(value: Any) -> Any:
            # Pass-through for non-current class types
            return value
            
        return core_schema.with_info_after_validator_function(
            validate,
            core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize, when_used='unless-none'),
        )
