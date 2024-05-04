import copy
import json
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from huggingface_hub import InferenceClient
from typing_extensions import Annotated

from autogen.agentchat import Agent, AssistantAgent, ConversableAgent, UserProxyAgent
from autogen.agentchat.contrib import img_utils
from autogen.oai.client import OpenAIWrapper


class HuggingFaceTask(Enum):
    # Computer vision
    IMAGE_CLASSIFICATION = "image-classification"
    IMAGE_SEGMENTATION = "image-segmentation"
    IMAGE_TO_IMAGE = "image-to-image"
    IMAGE_TO_TEXT = "image-to-text"
    OBJECT_DETECTION = "object-detection"
    TEXT_TO_IMAGE = "text-to-image"


class HuggingFaceAgent(ConversableAgent):

    DEFAULT_PROMPT = "You are a helpful AI assistant with multimodal capabilities (via the provided functions)."

    DEFAULT_DESCRIPTION = "A helpful assistant with multimodal capabilities. Ask them to perform image-to-text, text-to-image, speech-to-text, text-to-speech, and more!"

    DEFAULT_HF_TASK_LIST = list(HuggingFaceTask)

    def __init__(
        self,
        name: str,
        system_message: Optional[Union[str, List[str]]] = DEFAULT_PROMPT,
        description: Optional[str] = DEFAULT_DESCRIPTION,
        is_termination_msg: Optional[Callable[[Dict[str, Any]], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Union[Dict, Literal[False]] = False,
        llm_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        hf_task_list: Optional[List[Union[str, HuggingFaceTask]]] = DEFAULT_HF_TASK_LIST,
        hf_config: Optional[Dict[str, Union[str, Dict]]] = {},
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            description=description,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
        )

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
        self._hf_task_list = [HuggingFaceTask[t] if isinstance(t, str) else t for t in hf_task_list]
        self._hf_config = hf_config
        self._check_hf_config()

        self._hf_client = InferenceClient(
            token=self._hf_config.get("api_key", None),
            **self._hf_config.get("params", {}),
        )

        self._register_functions()

        self.register_reply([Agent, None], HuggingFaceAgent.generate_huggingface_reply, position=2)

    def _check_hf_config(self) -> None:
        valid_keys = [t.value for t in HuggingFaceTask] + ["api_key", "params"]
        for key in self._hf_config.keys():
            if key not in valid_keys:
                raise ValueError(f"Invalid key in hf_config: {key}. Valid keys are: {valid_keys}.")

    def _register_functions(self) -> None:
        # Helper functions
        def _load_task_config(task: HuggingFaceTask) -> Tuple[Union[str, None], Dict]:
            task_config = self._hf_config.get(task.value, {})
            model = task_config.get("model", None)
            params = task_config.get("params", {})
            return model, params

        if HuggingFaceTask.TEXT_TO_IMAGE in self._hf_task_list:

            @self._user_proxy.register_for_execution()
            @self._assistant.register_for_llm(
                name=HuggingFaceTask.TEXT_TO_IMAGE.value,
                description="Generates images from input text.",
            )
            def _text_to_image(text: Annotated[str, "The prompt to generate an image from"]) -> str:
                model, params = _load_task_config(HuggingFaceTask.TEXT_TO_IMAGE)
                image = self._hf_client.text_to_image(text, model=model, **params)
                response = {
                    "content": [
                        {"type": "text", "text": f"I generated an image with the prompt: {text}"},
                        {"type": "image_url", "image_url": {"url": img_utils.pil_to_data_uri(image)}},
                    ]
                }

                return json.dumps(response)

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

        self._user_proxy.send(messages[-1], self._assistant, request_reply=True, silent=True)
        agent_reply = self._user_proxy.chat_messages[self._assistant][-1]
        proxy_reply = self._user_proxy.generate_reply(
            messages=self._user_proxy.chat_messages[self._assistant], sender=self._assistant
        )

        if proxy_reply == "":
            # default reply
            return True, None if agent_reply is None else agent_reply["content"]
        else:
            # tool reply
            return True, None if proxy_reply is None else json.loads(proxy_reply["content"])
