from typing import Dict, List, Optional, Union

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


class VisionCapability(AgentCapability):
    """
        We can add vision capability to regular ConversableAgent, even if the agent does not have the multimodal capability,
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
    ):
        """
        Args:
            lmm_config (dict or False): LMM (multimodal) client configuration,
                which will be used to call LMM to describe the image.
        """
        assert lmm_config, "Vision Capability requires a valid lmm_config."
        self._lmm_config = lmm_config
        self._lmm_client = OpenAIWrapper(**lmm_config)

    def add_to_agent(self, agent: ConversableAgent):
        if isinstance(agent, MultimodalConversableAgent):
            print(
                colored(
                    "Warning: This agent is already a multimodal agent. The vision capability will not be added.",
                    "yellow",
                )
            )
            return  # do nothing
        self.parent_agent = agent

        # Register a hook for processing the last message.
        agent.register_hook(hookable_method="process_last_received_message", hook=self.process_last_received_message)

        # Was an lmm_config passed to the constructor?
        if self._lmm_config is None:
            # No. Use the agent's lmm_config.
            self._lmm_config = agent.lmm_config
        assert self._lmm_config, "Vision Capability requires a valid lmm_config."

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
                img_data = get_image_data(item["image_url"]["url"])
                img_caption = self._get_image_caption(img_data)
                aug_content += f'<img {item["image_url"]["url"]}> in case you can not see, the caption of this image is: {img_caption}\n'
            else:
                raise ValueError(f"Unsupported content type: {item['type']}")
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
                        {"type": "text", "text": "Describe the following image in details."},
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
