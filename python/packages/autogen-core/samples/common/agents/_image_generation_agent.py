from typing import Literal

import openai
from autogen_core.base import CancellationToken, MessageContext
from autogen_core.components import (
    DefaultTopicId,
    Image,
    RoutedAgent,
    message_handler,
)
from autogen_core.components.model_context import ChatCompletionContext
from autogen_core.components.models import UserMessage

from ..types import (
    MultiModalMessage,
    PublishNow,
    Reset,
    TextMessage,
)


class ImageGenerationAgent(RoutedAgent):
    """An agent that generates images using DALL-E models. It publishes the
    generated images as MultiModalMessage.

    Args:
        description (str): The description of the agent.
        model_context (ChatCompletionContext): The context manager for storing
            and retrieving ChatCompletion messages.
        client (openai.AsyncClient): The client to use for the OpenAI API.
        model (Literal["dall-e-2", "dall-e-3"], optional): The DALL-E model to use. Defaults to "dall-e-2".
    """

    def __init__(
        self,
        description: str,
        model_context: ChatCompletionContext,
        client: openai.AsyncClient,
        model: Literal["dall-e-2", "dall-e-3"] = "dall-e-2",
    ):
        super().__init__(description)
        self._client = client
        self._model = model
        self._model_context = model_context

    @message_handler
    async def on_text_message(self, message: TextMessage, ctx: MessageContext) -> None:
        """Handle a text message. This method adds the message to the memory."""
        await self._model_context.add_message(UserMessage(content=message.content, source=message.source))

    @message_handler
    async def on_reset(self, message: Reset, ctx: MessageContext) -> None:
        await self._model_context.clear()

    @message_handler
    async def on_publish_now(self, message: PublishNow, ctx: MessageContext) -> None:
        """Handle a publish now message. This method generates an image using a DALL-E model with
        a prompt. The prompt is a concatenation of all TextMessages in the memory. The generated
        image is published as a MultiModalMessage."""

        response = await self._generate_response(ctx.cancellation_token)
        await self.publish_message(response, topic_id=DefaultTopicId())

    async def _generate_response(self, cancellation_token: CancellationToken) -> MultiModalMessage:
        messages = await self._model_context.get_messages()
        if len(messages) == 0:
            return MultiModalMessage(
                content=["I need more information to generate an image."], source=self.metadata["type"]
            )
        prompt = ""
        for m in messages:
            assert isinstance(m.content, str)
            prompt += m.content + "\n"
        prompt.strip()
        response = await self._client.images.generate(model=self._model, prompt=prompt, response_format="b64_json")
        assert len(response.data) > 0 and response.data[0].b64_json is not None
        # Create a MultiModalMessage with the image.
        image = Image.from_base64(response.data[0].b64_json)
        multi_modal_message = MultiModalMessage(content=[image], source=self.metadata["type"])
        return multi_modal_message
