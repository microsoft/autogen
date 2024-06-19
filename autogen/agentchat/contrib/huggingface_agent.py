import copy
from enum import Flag, auto
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from typing_extensions import Annotated

from autogen import code_utils
from autogen.agentchat import Agent, AssistantAgent, ConversableAgent, UserProxyAgent
from autogen.agentchat.contrib import img_utils
from autogen.oai.client import OpenAIWrapper


class HuggingFaceCapability(Flag):
    # Computer vision
    TEXT_TO_IMAGE = auto()
    IMAGE_TO_IMAGE = auto()
    IMAGE_TO_TEXT = auto()
    VISUAL_QUESTION_ANSWERING = auto()


class HuggingFaceAgent(ConversableAgent):

    DEFAULT_PROMPT = """You are a helpful AI assistant with multimodal capabilities (via the provided functions).
If your response contains an image path, wrap it in an HTML image tag as: <img "path_to_image">
"""

    DEFAULT_DESCRIPTION = """A helpful assistant with multimodal capabilities. Ask them to perform image-to-text, text-to-image, speech-to-text, text-to-speech, and more!
"""

    DEFAULT_HF_CAPABILITY = (
        HuggingFaceCapability.TEXT_TO_IMAGE
        | HuggingFaceCapability.IMAGE_TO_IMAGE
        | HuggingFaceCapability.IMAGE_TO_TEXT
        | HuggingFaceCapability.VISUAL_QUESTION_ANSWERING
    )

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List[str]]] = DEFAULT_PROMPT,
        hf_capability: Optional[HuggingFaceCapability] = DEFAULT_HF_CAPABILITY,
        hf_capability_config_map: Optional[Dict[str, Dict[str, Any]]] = {},
        llm_config: Optional[Union[Dict, Literal[False], None]] = None,
        assistant_agent: Optional[Union[ConversableAgent, None]] = None,
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

        # Set up the inner monologue
        inner_llm_config = copy.deepcopy(llm_config)

        if assistant_agent is None:
            self._assistant = AssistantAgent(
                self.name + "_inner_assistant",
                system_message=system_message,
                llm_config=inner_llm_config,
                is_termination_msg=lambda x: False,
            )
        else:
            self._assistant = assistant_agent

        self._user_proxy = UserProxyAgent(
            self.name + "_inner_user_proxy",
            human_input_mode="NEVER",
            code_execution_config=False,
            default_auto_reply="",
            is_termination_msg=lambda x: False,
        )

        # Set up the HF InferenceClient
        self._hf_capability = hf_capability
        self._hf_clients = self._load_hf_capability_config(hf_capability, hf_capability_config_map)

        # Other configurations
        self._is_gpt4v_format = is_gpt4v_format
        self._is_silent = is_silent

        self._register_functions()

        self.register_reply([Agent, None], HuggingFaceAgent.generate_huggingface_reply, position=2)

    def _load_hf_capability_config(
        self, hf_capability: HuggingFaceCapability, hf_capability_config: Dict[str, Dict[str, Any]]
    ) -> Dict[str, OpenAIWrapper]:
        hf_clients = {}
        for _hf_cap in HuggingFaceCapability:
            if not hf_capability & _hf_cap:
                continue

            _hf_cap_config = hf_capability_config.get(_hf_cap)
            if _hf_cap_config is None:
                # Use default config
                _hf_cap_config = {"config_list": [{"api_type": "huggingface"}]}

            assert (
                "config_list" in _hf_cap_config
                and len(_hf_cap_config["config_list"]) > 0
                and all(config.get("api_type") == "huggingface" for config in _hf_cap_config["config_list"])
            ), "Invalid LLM config. Must set 'api_type' to 'huggingface' in the config_list."
            hf_clients[_hf_cap] = OpenAIWrapper(**_hf_cap_config)

        return hf_clients

    def _register_functions(self) -> None:

        if HuggingFaceCapability.TEXT_TO_IMAGE & self._hf_capability:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name=HuggingFaceCapability.TEXT_TO_IMAGE.name,
                description="Generates images from input text.",
            )
            def _text_to_image(text: Annotated[str, "The prompt to generate an image from."]) -> str:
                import tempfile

                client = self._hf_clients[HuggingFaceCapability.TEXT_TO_IMAGE]
                response = client.create(task="text-to-image", prompt=text)
                extracted_response = client.extract_text_or_completion_object(response)[0]
                image = img_utils.get_pil_image(extracted_response)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    image.save(temp_file.name)
                    response = f"I generated an image with the prompt: {text}"
                    response += f"<img {temp_file.name}>"

                return response

        if HuggingFaceCapability.IMAGE_TO_TEXT & self._hf_capability:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name=HuggingFaceCapability.IMAGE_TO_TEXT.name,
                description="Outputs a text from a given image. Image captioning or optical character recognition can be considered as the most common applications of image to text.",
            )
            def _image_to_text(
                image_file: Annotated[
                    str, "The path to the image file, a URL to an image, or a base64-encoded string of the image."
                ]
            ) -> str:
                client = self._hf_clients[HuggingFaceCapability.IMAGE_TO_TEXT]
                response = client.create(task="image-to-text", prompt="", image_file=image_file)
                generated_text = client.extract_text_or_completion_object(response)[0]
                response = f"I generated the following text from the image: {generated_text}"

                return response

        if HuggingFaceCapability.IMAGE_TO_IMAGE & self._hf_capability:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name=HuggingFaceCapability.IMAGE_TO_IMAGE.name,
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

                client = self._hf_clients[HuggingFaceCapability.IMAGE_TO_IMAGE]
                response = client.create(task="image-to-image", prompt=text, image_file=image_file)
                extracted_response = client.extract_text_or_completion_object(response)[0]
                tgt_image = img_utils.get_pil_image(extracted_response)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    tgt_image.save(temp_file.name)
                    response = f"I generated an image from the input image with the prompt: {text}"
                    response += f"<img {temp_file.name}>"

                return response

        if HuggingFaceCapability.VISUAL_QUESTION_ANSWERING & self._hf_capability:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name=HuggingFaceCapability.VISUAL_QUESTION_ANSWERING.name,
                description="Answers open-ended questions based on an image.",
            )
            def _visual_question_answering(
                image_file: Annotated[
                    str,
                    "The input image for the context. It can be a path, a URL, or a base64-encoded string of the image.",
                ],
                question: Annotated[str, "The question to be answered."],
            ) -> str:
                client = self._hf_clients[HuggingFaceCapability.VISUAL_QUESTION_ANSWERING]
                response = client.create(task="visual-question-answering", prompt=question, image_file=image_file)
                answer = client.extract_text_or_completion_object(response)[0]
                response = f"The answer to the question '{question}' is: {answer}"

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
            new_message = copy.deepcopy(message)
            new_message["content"] = code_utils.content_str(new_message["content"])
            self._assistant.chat_messages[self._user_proxy].append(new_message)

        proxy_reply = messages[-1]
        while True:
            self._user_proxy.send(proxy_reply, self._assistant, request_reply=True, silent=self._is_silent)
            assistant_reply = self._user_proxy.chat_messages[self._assistant][-1]
            proxy_reply = self._user_proxy.generate_reply(
                messages=self._user_proxy.chat_messages[self._assistant], sender=self._assistant
            )
            if proxy_reply == "":
                break

        if assistant_reply is not None and self._is_gpt4v_format:
            assistant_reply["content"] = img_utils.gpt4v_formatter(assistant_reply["content"], img_format="pil")

        return True, assistant_reply
