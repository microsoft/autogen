import copy
from typing import Dict, List, Literal, Optional, Protocol, Sequence, Union

from transformers import pipeline

from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib import img_utils
from autogen.cache import AbstractCache, Cache

from .transforms import MessageTransform

MODALITIES = ["text", "image", "video", "audio"]
ModalitiesType = Literal["text", "image", "video", "audio"]


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
        if isinstance(caption, list) and len(caption) > 0:
            return caption[0].get("generated_text", "")
        return output_caption


class ImageAdapter:
    def __init__(
        self,
        image_captioner: Optional[ImageCaptioner],
        caption_template: str = "(You received an image {idx}/? and here is the caption: \n{caption}.)",
    ):
        self._captioner = image_captioner
        self._caption_template = caption_template

    def apply_transform(self, messages: List[Dict], **kwargs) -> List[Dict]:
        for message in messages:
            if not message.get("content") or message["content"] is None:
                return messages

            if not isinstance(message["content"], (list, str)):
                return messages

            if "image" in kwargs.get("supported_modalities", []):
                message["content"] = self._convert_tags_to_multimodal_content(message["content"])

            else:
                if self._captioner:
                    message["content"] = self._convert_images_to_text(message["content"])

        return messages

    def _convert_tags_to_multimodal_content(
        self, content: Union[str, List[Union[Dict, str]]]
    ) -> List[Union[Dict, str]]:
        if isinstance(content, str):
            return img_utils.gpt4v_formatter(content)

        new_content = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    new_content.extend(img_utils.gpt4v_formatter(item))
                else:
                    if "text" in item:
                        new_content.extend(img_utils.gpt4v_formatter(item["text"]))
                    else:
                        new_content.append(item)

        return new_content

    def _convert_images_to_text(self, content: Union[str, List[Union[Dict, str]]]) -> List[Union[Dict, str]]:
        assert self._captioner

        if isinstance(content, str):
            return [content]

        if isinstance(content, list) and len(content) > 0 and isinstance(content[0], str):
            return content

        output_captions = ""
        img_number = 1
        txt_idx = None
        for idx, item in enumerate(content):
            if not isinstance(item, dict):
                continue

            if item.get("type") == "text":
                txt_idx = idx

            if item.get("type") == "image_url":
                img = item["image_url"]["url"]
                caption = self._captioner.caption_image(img)
                output_captions += self._caption_template.format(idx=img_number, caption=caption) + "\n"
                img_number += 1

        if txt_idx is not None:
            assert len(content) > 0
            content[txt_idx]["text"] += output_captions
        else:
            content.insert(0, {"type": "text", "text": output_captions})

        return content


class DropUnsupportedModalities:
    def apply_transform(self, messages: List[Dict], **kwargs) -> List[Dict]:
        if not kwargs.get("supported_modalities", []):
            return messages

        for message in messages:
            if message.get("content") is None or isinstance(message["content"], str):
                continue

            if not isinstance(message["content"], list):
                continue

            new_content = []
            for item in message["content"]:
                if isinstance(item, dict):
                    if item.get("type") in kwargs["supported_modalities"]:
                        new_content.append(item)

            message["content"] = new_content

        return messages
