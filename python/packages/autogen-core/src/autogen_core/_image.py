from __future__ import annotations

import base64
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, cast

from PIL import Image as PILImage
from pydantic import GetCoreSchemaHandler, ValidationInfo
from pydantic_core import core_schema
from typing_extensions import Literal

from ._media import Media


class Image(Media):
    """Represents an image that can be sent to an LLM.

    Example:

        Loading an image from a URL:

        .. code-block:: python

            from autogen_core import Image
            from PIL import Image as PILImage
            import aiohttp
            import asyncio


            async def from_url(url: str) -> Image:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        content = await response.read()
                        return Image.from_pil(PILImage.open(BytesIO(content)))


            image = asyncio.run(from_url("https://example.com/image"))

    """

    media_type = "image"

    def __init__(self, image: PILImage.Image):
        self.image: PILImage.Image = image.convert("RGB")

    @classmethod
    def from_pil(cls, pil_image: PILImage.Image) -> Image:
        """Create an Image object from a PIL Image."""
        return cls(pil_image)

    @classmethod
    def from_uri(cls, uri: str) -> Image:
        """Create an Image object from a data URI."""
        if not re.match(r"data:image/(?:png|jpeg);base64,", uri):
            raise ValueError("Invalid URI format. It should be a base64 encoded image URI.")

        base64_data = cls._extract_base64_from_data_uri(uri)
        return cls.from_base64(base64_data)

    @classmethod
    def from_base64(cls, base64_str: str) -> Image:
        """Create an Image object from a base64 encoded string."""
        return cls(PILImage.open(BytesIO(base64.b64decode(base64_str))))

    def to_base64(self) -> str:
        """Convert the image to a base64 encoded string."""
        buffered = BytesIO()
        self.image.save(buffered, format="PNG")
        content = buffered.getvalue()
        return base64.b64encode(content).decode("utf-8")

    @classmethod
    def from_file(cls, file_path: Path) -> Image:
        """Create an Image object from a file path."""
        return cls(PILImage.open(file_path))

    def to_data_uri(self) -> str:
        """Convert the image to a data URI."""
        base64_str = self.to_base64()
        return f"data:image/png;base64,{base64_str}"

    # Returns formatted object for OpenAI API
    def to_openai_format(self, detail: Literal["auto", "low", "high"] = "auto") -> Dict[str, Any]:
        """Convert the image to the format expected by OpenAI API."""
        return {"type": "image_url", "image_url": {"url": self.to_data_uri(), "detail": detail}}

    def _repr_html_(self) -> str:
        """Show the image in Jupyter notebook."""
        return f'<img src="{self.to_data_uri()}"/>'

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        """Pydantic validation schema with passthrough for other Media types."""
        
        # Custom validation specific to Image
        def validate(value: Any, validation_info: ValidationInfo) -> Any:
            # Check if value is another Media subclass first (allow passthrough)
            for subclass_name, subclass in Media._subclasses.items():
                if subclass_name != "Image" and isinstance(value, subclass):
                    return value
            
            # Now handle Image-specific cases
            if isinstance(value, dict):
                base64_data = cast(str | None, value.get("data"))
                if base64_data is None:
                    raise ValueError("Expected 'data' key in the dictionary")
                try:
                    return cls.from_base64(base64_data)
                except Exception as e:
                    raise ValueError(f"Invalid base64 image data: {e}")
            elif isinstance(value, cls):
                return value
            else:
                raise TypeError(f"Expected dict, {cls.__name__} instance, or another Media type, got {type(value)}")

        # Custom serialization
        def serialize(value: Any) -> Any:
            if isinstance(value, Image):
                return {"data": value.to_base64()}
            # For other Media types, let their own serializers handle it
            return value

        return core_schema.with_info_after_validator_function(
            validate,
            core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize, when_used='unless-none'),
        )
