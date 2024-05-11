import copy
import json
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from huggingface_hub import ImageToTextOutput, InferenceClient
from typing_extensions import Annotated

from autogen.agentchat import Agent, AssistantAgent, ConversableAgent, UserProxyAgent
from autogen.agentchat.contrib import img_utils
from autogen.oai.client import OpenAIWrapper


class HuggingFaceCapability(Enum):
    # Computer vision
    IMAGE_TO_IMAGE = "image-to-image"
    IMAGE_TO_TEXT = "image-to-text"
    TEXT_TO_IMAGE = "text-to-image"


class HuggingFaceAgent(ConversableAgent):

    DEFAULT_PROMPT = """You are a helpful AI assistant with multimodal capabilities (via the provided functions).
If your response contains an image path, wrap it in an HTML image tag as: <img "path_to_image">
"""

    DEFAULT_DESCRIPTION = """A helpful assistant with multimodal capabilities. Ask them to perform image-to-text, text-to-image, speech-to-text, text-to-speech, and more!
"""

    DEFAULT_HF_CAPABILITY_LIST = list(HuggingFaceCapability)

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List[str]]] = DEFAULT_PROMPT,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        hf_capability_list: Optional[List[Union[str, HuggingFaceCapability]]] = DEFAULT_HF_CAPABILITY_LIST,
        hf_config: Optional[Dict[str, Union[str, Dict]]] = {},
        is_gpt4v_format: Optional[bool] = False,
        is_silent: Optional[bool] = True,
        **kwargs,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            **kwargs,
        )

        self._is_gpt4v_format = is_gpt4v_format
        self._is_silent = is_silent

        # Set up the inner monologue
        inner_llm_config = copy.deepcopy(llm_config)

        self._assistant = AssistantAgent(
            self.name + "_inner_assistant",
            system_message=system_message,
            llm_config=inner_llm_config,
            is_termination_msg=lambda x: False,
        )

        self._user_proxy = UserProxyAgent(
            self.name + "_inner_user_proxy",
            human_input_mode="NEVER",
            code_execution_config=False,
            default_auto_reply="",
            is_termination_msg=lambda x: False,
        )

        # Set up the HF InferenceClient
        self._hf_capability_list = [HuggingFaceCapability[t] if isinstance(t, str) else t for t in hf_capability_list]
        self._hf_config = hf_config
        self._check_hf_config()

        self._hf_client = InferenceClient(
            token=self._hf_config.get("api_key", None),
            **self._hf_config.get("params", {}),
        )

        self._register_functions()

        self.register_reply([Agent, None], HuggingFaceAgent.generate_huggingface_reply, position=2)

    def _check_hf_config(self) -> None:
        valid_keys = [t.value for t in HuggingFaceCapability] + ["api_key", "params"]
        for key in self._hf_config.keys():
            if key not in valid_keys:
                raise ValueError(f"Invalid key in hf_config: {key}. Valid keys are: {valid_keys}.")

    def _register_functions(self) -> None:
        # Helper functions
        def _load_capability_config(capability: HuggingFaceCapability) -> Tuple[Union[str, None], Dict]:
            capability_config = self._hf_config.get(capability.value, {})
            model = capability_config.get("model", None)
            params = capability_config.get("params", {})
            return model, params

        if HuggingFaceCapability.TEXT_TO_IMAGE in self._hf_capability_list:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name=HuggingFaceCapability.TEXT_TO_IMAGE.value,
                description="Generates images from input text.",
            )
            def _text_to_image(text: Annotated[str, "The prompt to generate an image from"]) -> str:
                import tempfile

                model, params = _load_capability_config(HuggingFaceCapability.TEXT_TO_IMAGE)
                image = self._hf_client.text_to_image(text, model=model, **params)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    image.save(temp_file.name)
                    response = f"I generated an image with the prompt: {text}"
                    response += f"<img {temp_file.name}>"

                return response

        if HuggingFaceCapability.IMAGE_TO_TEXT in self._hf_capability_list:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name=HuggingFaceCapability.IMAGE_TO_TEXT.value,
                description="Outputs a text from a given image. Image captioning or optical character recognition can be considered as the most common applications of image to text.",
            )
            def _image_to_text(
                image_file: Annotated[
                    str, "The path to the image file, a URL to an image, or a base64-encoded string of the image"
                ]
            ) -> str:
                model, params = _load_capability_config(HuggingFaceCapability.IMAGE_TO_TEXT)
                image_data = img_utils.get_image_data(image_file, use_b64=False)
                raw_response = self._hf_client.post(
                    data=image_data,
                    model=model,
                    task=HuggingFaceCapability.IMAGE_TO_TEXT.value,
                )
                generated_text = ImageToTextOutput.parse_obj_as_list(raw_response)[0].generated_text
                response = f"I generated the following text from the image: {generated_text}"

                return response

        if HuggingFaceCapability.IMAGE_TO_IMAGE in self._hf_capability_list:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name=HuggingFaceCapability.IMAGE_TO_IMAGE.value,
                description="Transforms a source image to match the characteristics of a target image or a target image domain.",
            )
            def _image_to_image(
                image_file: Annotated[
                    str,
                    "The input image for translation. It can be raw bytes, an image file, or a URL to an online image.",
                ],
                text: Annotated[str, "The text prompt to guide the image generation."],
            ) -> str:
                import tempfile

                model, params = _load_capability_config(HuggingFaceCapability.IMAGE_TO_IMAGE)
                image_data = img_utils.get_image_data(image_file, use_b64=False)
                tgt_image = self._hf_client.image_to_image(image_data, prompt=text, model=model, **params)

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    tgt_image.save(temp_file.name)
                    response = f"I generated an image from the input image with the prompt: {text}"
                    response += f"<img {temp_file.name}>"

                return response

    def generate_huggingface_reply(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        if messages is None:
            messages = self._oai_messages[sender]

        self._assistant.reset()
        self._user_proxy.reset()

        # Clone the messages to give context
        self._assistant.chat_messages[self._user_proxy] = list()
        history = messages[0 : len(messages) - 1]
        for message in history:
            self._assistant.chat_messages[self._user_proxy].append(message)

        proxy_reply = messages[-1]
        while True:
            self._user_proxy.send(proxy_reply, self._assistant, request_reply=True, silent=self._is_silent)
            assistant_reply = self._user_proxy.chat_messages[self._assistant][-1]
            proxy_reply = self._user_proxy.generate_reply(
                messages=self._user_proxy.chat_messages[self._assistant], sender=self._assistant
            )
            if proxy_reply == "":
                break
            elif self._is_gpt4v_format:
                proxy_reply["content"] = img_utils.gpt4v_formatter(proxy_reply["content"], img_format="pil")

        if assistant_reply is not None and self._is_gpt4v_format:
            assistant_reply["content"] = img_utils.gpt4v_formatter(assistant_reply["content"], img_format="pil")

        return True, assistant_reply
