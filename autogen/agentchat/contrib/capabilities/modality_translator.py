import copy
from typing import Dict, List, Literal, Optional, Protocol, Sequence

from transformers import pipeline

from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib import img_utils
from autogen.cache import AbstractCache, Cache

MODALITIES = ["text", "image", "video", "audio"]
ModalitiesType = Literal["text", "image", "video", "audio"]


class Translator(Protocol):
    def translate(self, message: Dict, *args, **kwargs) -> Dict: ...

    @property
    def translate_from(self) -> ModalitiesType: ...

    @property
    def translate_to(self) -> ModalitiesType: ...


class TextToImage:
    def translate(self, message: Dict, *args, **kwargs) -> Dict:
        if not message.get("content"):
            return message

        message["content"] = img_utils.gpt4v_formatter(message["content"])
        return message

    @property
    def translate_from(self) -> ModalitiesType:
        return "text"

    @property
    def translate_to(self) -> ModalitiesType:
        return "image"


class ImageToText:
    def __init__(self, model: str = "Salesforce/blip-image-captioning-base"):
        self._captioner = pipeline("image-to-text", model=model)
        self._caption_template = "(You received an image {idx}/? and here is the caption: \n{caption}.)"

    def translate(self, message: Dict, *args, **kwargs) -> Dict:
        if not message.get("content") or message["content"] is None:
            return message

        if isinstance(message["content"], (str)):
            return message

        output_captions = ""
        img_number = 1
        txt_idx = None
        for idx, content in enumerate(message["content"]):
            if content["type"] == "text":
                txt_idx = idx

            if content["type"] == "image_url":
                img = content["image_url"]["url"]
                caption = self._captioner(img)
                caption = caption[0]["generated_text"]
                output_captions += self._caption_template.format(idx=img_number, caption=caption)
                img_number += 1

        if txt_idx is not None:
            message["content"][txt_idx]["text"] += output_captions
        else:
            message["content"].insert(0, {"type": "text", "text": output_captions})

        return message

    @property
    def translate_from(self) -> ModalitiesType:
        return "image"

    @property
    def translate_to(self) -> ModalitiesType:
        return "text"


class ModalityTranslator:
    def __init__(
        self,
        modalities: Sequence[str],
        translators: List[Translator],
        cache: Optional[AbstractCache] = Cache.disk(),
    ):
        self._modalities = set(modalities)
        self._translators = translators
        self._cache = cache

        for translator in translators:
            _validate_modalities(translator)

        if "image" in modalities and "text" in modalities:
            self._modalities.add("image_url")

    def add_to_agent(self, agent: ConversableAgent):
        """Adds the message transformations capability to the specified ConversableAgent.

        This function performs the following modifications to the agent:

        1. Registers a hook that automatically transforms all messages before they are processed for
            response generation.
        """
        agent.register_hook(hookable_method="process_all_messages_before_reply", hook=self._translate_modalities)

    def _translate_modalities(self, messages: List[Dict]) -> List[Dict]:
        translated_messages = copy.deepcopy(messages)
        system_message = None

        if messages[0]["role"] == "system":
            system_message = copy.deepcopy(messages[0])
            translated_messages.pop(0)

        for translator in self._translators:
            for message in translated_messages:
                message = translator.translate(message)

        translated_messages = self._clean_messages(translated_messages)

        if system_message:
            translated_messages.insert(0, system_message)

        return translated_messages

    def _clean_messages(self, messages: List[Dict]) -> List[Dict]:
        for message in messages:
            if message.get("content") is None or isinstance(message["content"], str):
                continue

            message["content"] = [content for content in message["content"] if content["type"] in self._modalities]

        return messages


def _validate_modalities(translator: Translator):
    assert (
        translator.translate_from != translator.translate_to
    ), "You must be translating between two different modalities"
