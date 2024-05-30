from typing import Dict, List, Literal, Optional, Sequence, Set, Tuple, Union

from autogen.agentchat.contrib import img_utils
from autogen.agentchat.utils import parse_tags_from_content, replace_tag_in_content
from autogen.cache.cache import AbstractCache, Cache

from .image_captioners import ImageCaptioner

ModalitiesType = Literal["text", "image", "video", "audio"]
MODALITIES_ALIAS: Dict[ModalitiesType, List[str]] = {
    "text": ["text"],
    "image": ["image", "image_url"],
    "video": ["video"],
    "audio": ["audio"],
}


class ImageModality:
    def __init__(
        self,
        image_captioner: Optional[ImageCaptioner] = None,
        caption_template: str = "(You received an image and here is the caption: {caption}.)",
        agent_has_image_modality: bool = False,
        drop_unsupported_message_format: bool = True,
        cache: AbstractCache = Cache.disk(),
    ):
        self._validate_modality_support(agent_has_image_modality, drop_unsupported_message_format, image_captioner)

        self._captioner = image_captioner
        self._caption_template = caption_template
        self._agent_has_image_modality = agent_has_image_modality

        drop_unsupported_transform = _drop_unsupported_factory(
            unsupported_agent_modalities=["image"] if not agent_has_image_modality else None,
            modalities_alias=MODALITIES_ALIAS,
        )

        self._drop_unsupported = drop_unsupported_transform if drop_unsupported_message_format else None
        self._cache = cache

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        for message in messages:
            if not message.get("content") or message["content"] is None:
                return messages

            if not isinstance(message["content"], (list, str)):
                return messages

            if self._agent_has_image_modality:
                message["content"] = self._convert_tags_to_multimodal_content(message["content"])

            else:
                assert self._captioner, "Must provide an image captioner to convert images to text."
                message["content"] = self._replace_images_with_captions(message["content"])
                message["content"] = self._replace_tags_with_captions(message["content"])

        if self._drop_unsupported:
            # We want to only drop the image types
            messages = self._drop_unsupported.apply_transform(messages)

        return messages

    def get_logs(self, pre_transform_messages: List[Dict], post_transform_messages: List[Dict]) -> Tuple[str, bool]:
        return "No logs for this modality.", False

    def _convert_tags_to_multimodal_content(
        self, content: Union[str, List[Union[Dict, str]]]
    ) -> List[Union[Dict, str]]:
        if isinstance(content, str):
            return img_utils.gpt4v_formatter(content)

        modified_content = []
        if isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    modified_content.extend(img_utils.gpt4v_formatter(item))
                else:
                    if "text" in item:
                        modified_content.extend(img_utils.gpt4v_formatter(item["text"]))
                    else:
                        modified_content.append(item)

        return modified_content

    def _replace_tags_with_captions(
        self, content: Union[str, List[Union[Dict, str]]]
    ) -> Union[List[Union[Dict, str]], str]:
        assert self._captioner
        for tag in parse_tags_from_content("img", content):
            try:
                caption = self._captioner.caption_image(tag["attr"]["src"])
                replacement_text = self._caption_template.format(caption=caption)
            except Exception:
                replacement_text = (
                    "(You failed to convert the image tag to text. "
                    f"Possibly due to invalid image source {tag['attr']['src']}.)"
                )
            content = replace_tag_in_content(tag, content, replacement_text)
        return content

    def _replace_images_with_captions(self, content: Union[str, List[Union[Dict, str]]]) -> List[Union[Dict, str]]:
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
                try:
                    caption = self._captioner.caption_image(img)
                    output_captions += self._caption_template.format(idx=img_number, caption=caption) + "\n"
                except Exception:
                    output_captions += f"(Failed to generate caption for image {img_number}.)\n"

                img_number += 1

        output_captions = output_captions.format(total=img_number - 1)

        if output_captions == "":
            return content

        if txt_idx is not None:
            assert len(content) > 0
            content[txt_idx]["text"] += output_captions
        else:
            content.insert(0, {"type": "text", "text": output_captions})

        return content

    def _validate_modality_support(
        self, agent_has_image_modality: bool, drop_unsupported: bool, image_captioner: Optional[ImageCaptioner]
    ) -> None:
        if agent_has_image_modality and drop_unsupported:
            raise ValueError("Cannot drop unsupported modalities when the agent has an image modality.")

        if not image_captioner and not agent_has_image_modality:
            raise ValueError("Must provide an image captioner when the agent does not have an image modality.")


class DropUnsupportedModalities:
    def __init__(self, supported_modalities: Sequence[ModalitiesType] = list()):
        self._supported_modalities = _expand_supported_modalities(supported_modalities, MODALITIES_ALIAS)

    def apply_transform(self, messages: List[Dict]) -> List[Dict]:
        for message in messages:
            if message.get("content") is None or isinstance(message["content"], str):
                continue

            if not isinstance(message["content"], list):
                continue

            new_content = []
            for item in message["content"]:
                if not isinstance(item, dict):
                    continue

                if item.get("type") in self._supported_modalities:
                    new_content.append(item)

            message["content"] = new_content
        return messages


def _drop_unsupported_factory(
    unsupported_agent_modalities: Optional[List[ModalitiesType]], modalities_alias: Dict[ModalitiesType, List[str]]
) -> DropUnsupportedModalities:
    """
    Determines the supported modalities and returns an instance of DropUnsupportedModalities if necessary.

    Parameters:
    - agent_modalities (Optional[List[ModalitiesType]]): List of modalities supported by the agent, or None if no modalities are supported.
    - modalities_alias (Dict[ModalitiesType, List[str]]): Dictionary mapping modalities to their aliases.

    Returns:
    - DropUnsupportedModalities instance if any modalities are unsupported, else None.
    """
    if unsupported_agent_modalities is not None:
        supported_modalities: List[ModalitiesType] = [
            modal for modal in modalities_alias.keys() if modal not in unsupported_agent_modalities
        ]
    else:
        supported_modalities: List[ModalitiesType] = list(modalities_alias.keys())

    return DropUnsupportedModalities(supported_modalities)


def _expand_supported_modalities(
    supported_modalities: Sequence[ModalitiesType], modalities_mapping: Dict[ModalitiesType, List[str]]
) -> Set[str]:
    expanded_modalities = set()
    for modality in supported_modalities:
        expanded_modalities.update(modalities_mapping.get(modality, []))
    return expanded_modalities
