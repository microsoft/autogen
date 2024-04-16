from __future__ import annotations

import base64
import re
from io import BytesIO
from pathlib import Path

import aiohttp
from openai.types.chat import ChatCompletionContentPartImageParam
from PIL import Image as PILImage
from typing_extensions import Literal


class Image:
    def __init__(self, image: PILImage.Image):
        self.image: PILImage.Image = image.convert("RGB")

    @classmethod
    def from_pil(cls, pil_image: PILImage.Image) -> Image:
        return cls(pil_image)

    @classmethod
    def from_uri(cls, uri: str) -> Image:
        if not re.match(r"data:image/(?:png|jpeg);base64,", uri):
            raise ValueError("Invalid URI format. It should be a base64 encoded image URI.")

        # A URI. Remove the prefix and decode the base64 string.
        base64_data = re.sub(r"data:image/(?:png|jpeg);base64,", "", uri)
        return cls.from_base64(base64_data)

    @classmethod
    async def from_url(cls, url: str) -> Image:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.read()
                return cls(PILImage.open(content))

    @classmethod
    def from_base64(cls, base64_str: str) -> Image:
        return cls(PILImage.open(BytesIO(base64.b64decode(base64_str))))

    @classmethod
    def from_file(cls, file_path: Path) -> Image:
        return cls(PILImage.open(file_path))

    def _repr_html_(self) -> str:
        # Show the image in Jupyter notebook
        return f'<img src="{self.data_uri}"/>'

    @property
    def data_uri(self) -> str:
        buffered = BytesIO()
        self.image.save(buffered, format="PNG")
        content = buffered.getvalue()
        return _convert_base64_to_data_uri(base64.b64encode(content).decode("utf-8"))

    def to_openai_format(self, detail: Literal["auto", "low", "high"] = "auto") -> ChatCompletionContentPartImageParam:
        return {"type": "image_url", "image_url": {"url": self.data_uri, "detail": detail}}


def _convert_base64_to_data_uri(base64_image: str) -> str:
    def _get_mime_type_from_data_uri(base64_image: str) -> str:
        # Decode the base64 string
        image_data = base64.b64decode(base64_image)
        # Check the first few bytes for known signatures
        if image_data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
            return "image/gif"
        elif image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"  # use jpeg for unknown formats, best guess.

    mime_type = _get_mime_type_from_data_uri(base64_image)
    data_uri = f"data:{mime_type};base64,{base64_image}"
    return data_uri
