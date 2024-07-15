from typing import Literal

import openai
from agnext.components import (
    Image,
    TypeRoutedAgent,
    message_handler,
)
from agnext.components.memory import ChatMemory
from agnext.core import CancellationToken

from ..types import (
    Message,
    MultiModalMessage,
    PublishNow,
    Reset,
    TextMessage,
)


class ImageGenerationAgent(TypeRoutedAgent):
    """An agent that generates images using DALL-E models. It publishes the
    generated images as MultiModalMessage.

    Args:
        description (str): The description of the agent.
        memory (ChatMemory[Message]): The memory to store and retrieve messages.
        client (openai.AsyncClient): The client to use for the OpenAI API.
        model (Literal["dall-e-2", "dall-e-3"], optional): The DALL-E model to use. Defaults to "dall-e-2".
    """

    def __init__(
        self,
        description: str,
        memory: ChatMemory[Message],
        client: openai.AsyncClient,
        model: Literal["dall-e-2", "dall-e-3"] = "dall-e-2",
    ):
        super().__init__(description)
        self._client = client
        self._model = model
        self._memory = memory

    @message_handler
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        """Handle a text message. This method adds the message to the memory."""
        await self._memory.add_message(message)

    @message_handler
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        await self._memory.clear()

    @message_handler
    async def on_publish_now(self, message: PublishNow, cancellation_token: CancellationToken) -> None:
        """Handle a publish now message. This method generates an image using a DALL-E model with
        a prompt. The prompt is a concatenation of all TextMessages in the memory. The generated
        image is published as a MultiModalMessage."""

        response = await self._generate_response(cancellation_token)
        await self.publish_message(response)

    async def _generate_response(self, cancellation_token: CancellationToken) -> MultiModalMessage:
        messages = await self._memory.get_messages()
        if len(messages) == 0:
            return MultiModalMessage(
                content=["I need more information to generate an image."], source=self.metadata["name"]
            )
        prompt = ""
        for m in messages:
            assert isinstance(m, TextMessage)
            prompt += m.content + "\n"
        prompt.strip()
        response = await self._client.images.generate(model=self._model, prompt=prompt, response_format="b64_json")
        assert len(response.data) > 0 and response.data[0].b64_json is not None
        # Create a MultiModalMessage with the image.
        image = Image.from_base64(response.data[0].b64_json)
        multi_modal_message = MultiModalMessage(content=[image], source=self.metadata["name"])
        return multi_modal_message
