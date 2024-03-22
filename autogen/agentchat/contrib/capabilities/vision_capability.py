import copy
from typing import Callable, Dict, List, Optional, Union

from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.contrib.img_utils import (
    convert_base64_to_data_uri,
    get_image_data,
    get_pil_image,
    gpt4v_formatter,
    message_formatter_pil_to_b64,
)
from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent
from autogen.agentchat.conversable_agent import colored
from autogen.code_utils import content_str
from autogen.oai.client import OpenAIWrapper

DEFAULT_DESCRIPTION_PROMPT = (
    "Write a detailed caption for this image. "
    "Pay special attention to any details that might be useful or relevant "
    "to the ongoing conversation."
)


class VisionCapability(AgentCapability):
    """We can add vision capability to regular ConversableAgent, even if the agent does not have the multimodal capability,
    such as GPT-3.5-turbo agent, Llama, Orca, or Mistral agents. This vision capability will invoke a LMM client to describe
    the image (captioning) before sending the information to the agent's actual client.

        The vision capability will hook to the ConversableAgent's `process_last_received_message`.

        Some technical details:
        When the agent (who has the vision capability) received an message, it will:
        1. _process_received_message:
            a. _append_oai_message
        2. generate_reply: if the agent is a MultimodalAgent, it will also use the image tag.
            a. hook process_last_received_message (NOTE: this is where the vision capability will be hooked to.)
            b. hook process_all_messages_before_reply
        3. send:
            a. hook process_message_before_send
            b. _append_oai_message
    """

    def __init__(
        self,
        lmm_config: Dict,
        description_prompt: Optional[str] = DEFAULT_DESCRIPTION_PROMPT,
        custom_caption_func: Callable = None,
    ) -> None:
        """
        Initializes a new instance, setting up the configuration for interacting with
        a Language Multimodal (LMM) client and specifying optional parameters for image
        description and captioning.

        Args:
            lmm_config (Dict): Configuration for the LMM client, which is used to call
                the LMM service for describing the image. This must be a dictionary containing
                the necessary configuration parameters. If `lmm_config` is False or an empty dictionary,
                it is considered invalid, and initialization will assert.
            description_prompt (Optional[str], optional): The prompt to use for generating
                descriptions of the image. This parameter allows customization of the
                prompt passed to the LMM service. Defaults to `DEFAULT_DESCRIPTION_PROMPT` if not provided.
            custom_caption_func (Callable, optional): A callable that, if provided, will be used
                to generate captions for images. This allows for custom captioning logic outside
                of the standard LMM service interaction.
                The callable should take three parameters as input:
                    1. an image URL (or local location)
                    2. image_data (a PIL image)
                    3. lmm_client (to call remote LMM)
                and then return a description (as string).
                If not provided, captioning will rely on the LMM client configured via `lmm_config`.
                If provided, we will not run the default self._get_image_caption method.

        Raises:
            AssertionError: If neither a valid `lmm_config` nor a `custom_caption_func` is provided,
                an AssertionError is raised to indicate that the Vision Capability requires
                one of these to be valid for operation.
        """
        self._lmm_config = lmm_config
        self._description_prompt = description_prompt
        self._parent_agent = None

        if lmm_config:
            self._lmm_client = OpenAIWrapper(**lmm_config)
        else:
            self._lmm_client = None

        self._custom_caption_func = custom_caption_func
        assert (
            self._lmm_config or custom_caption_func
        ), "Vision Capability requires a valid lmm_config or custom_caption_func."

    def add_to_agent(self, agent: ConversableAgent) -> None:
        self._parent_agent = agent

        # Append extra info to the system message.
        agent.update_system_message(agent.system_message + "\nYou've been given the ability to interpret images.")

        # Register a hook for processing the last message.
        agent.register_hook(hookable_method="process_last_received_message", hook=self.process_last_received_message)

    def process_last_received_message(self, content: Union[str, List[dict]]) -> str:
        """
        Processes the last received message content by normalizing and augmenting it
        with descriptions of any included images. The function supports input content
        as either a string or a list of dictionaries, where each dictionary represents
        a content item (e.g., text, image). If the content contains image URLs, it
        fetches the image data, generates a caption for each image, and inserts the
        caption into the augmented content.

        The function aims to transform the content into a format compatible with GPT-4V
        multimodal inputs, specifically by formatting strings into PIL-compatible
        images if needed and appending text descriptions for images. This allows for
        a more accessible presentation of the content, especially in contexts where
        images cannot be displayed directly.

        Args:
            content (Union[str, List[dict]]): The last received message content, which
                can be a plain text string or a list of dictionaries representing
                different types of content items (e.g., text, image_url).

        Returns:
            str: The augmented message content

        Raises:
            AssertionError: If an item in the content list is not a dictionary.

        Examples:
            Assuming `self._get_image_caption(img_data)` returns
            "A beautiful sunset over the mountains" for the image.

        - Input as String:
            content = "Check out this cool photo!"
            Output: "Check out this cool photo!"
            (Content is a string without an image, remains unchanged.)

        - Input as String, with image location:
            content = "What's weather in this cool photo: <img http://example.com/photo.jpg>"
            Output: "What's weather in this cool photo: <img http://example.com/photo.jpg> in case you can not see, the caption of this image is:
            A beautiful sunset over the mountains\n"
            (Caption added after the image)

        - Input as List with Text Only:
            content = [{"type": "text", "text": "Here's an interesting fact."}]
            Output: "Here's an interesting fact."
            (No images in the content, it remains unchanged.)

        - Input as List with Image URL:
            content = [
                {"type": "text", "text": "What's weather in this cool photo:"},
                {"type": "image_url", "image_url": {"url": "http://example.com/photo.jpg"}}
            ]
            Output: "What's weather in this cool photo: <img http://example.com/photo.jpg> in case you can not see, the caption of this image is:
            A beautiful sunset over the mountains\n"
            (Caption added after the image)
        """
        copy.deepcopy(content)
        # normalize the content into the gpt-4v format for multimodal
        # we want to keep the URL format to keep it concise.
        if isinstance(content, str):
            content = gpt4v_formatter(content, img_format="url")

        aug_content: str = ""
        for item in content:
            assert isinstance(item, dict)
            if item["type"] == "text":
                aug_content += item["text"]
            elif item["type"] == "image_url":
                img_url = item["image_url"]["url"]
                img_caption = ""

                if self._custom_caption_func:
                    img_caption = self._custom_caption_func(img_url, get_pil_image(img_url), self._lmm_client)
                elif self._lmm_client:
                    img_data = get_image_data(img_url)
                    img_caption = self._get_image_caption(img_data)
                else:
                    img_caption = ""

                aug_content += f"<img {img_url}> in case you can not see, the caption of this image is: {img_caption}\n"
            else:
                print(f"Warning: the input type should either be `test` or `image_url`. Skip {item['type']} here.")

        return aug_content

    def _get_image_caption(self, img_data: str) -> str:
        """
        Args:
            img_data (str): base64 encoded image data.
        Returns:
            str: caption for the given image.
        """
        response = self._lmm_client.create(
            context=None,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._description_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": convert_base64_to_data_uri(img_data),
                            },
                        },
                    ],
                }
            ],
        )
        description = response.choices[0].message.content
        return content_str(description)
