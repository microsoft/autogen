from typing import Dict, List, Literal, Optional, Protocol, Union

from transformers import pipeline


class ImageCaptioner(Protocol):
    def caption_image(self, image_url: str) -> str: ...


class HuggingFaceImageCaptioner:
    def __init__(
        self,
        model: str = "Salesforce/blip-image-captioning-base",
    ):
        self._captioner = pipeline("image-to-text", model=model)

    def caption_image(self, image_url: str) -> str:
        output_caption = ""
        caption = self._captioner(image_url)
        if isinstance(caption, list) and len(caption) > 0 and isinstance(caption[0], dict):
            output_caption = caption[0].get("generated_text", "")

        return output_caption
