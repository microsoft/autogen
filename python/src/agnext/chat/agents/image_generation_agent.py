from typing import Literal

import openai

from ...components import (
    Image,
    TypeRoutedAgent,
    message_handler,
)
from ...core import CancellationToken
from ..memory import ChatMemory
from ..types import (
    MultiModalMessage,
    PublishNow,
    Reset,
    TextMessage,
)


class ImageGenerationAgent(TypeRoutedAgent):
    def __init__(
        self,
        description: str,
        memory: ChatMemory,
        client: openai.AsyncClient,
        model: Literal["dall-e-2", "dall-e-3"] = "dall-e-2",
    ):
        super().__init__(description)
        self._client = client
        self._model = model
        self._memory = memory

    @message_handler
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        await self._memory.add_message(message)

    @message_handler
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        await self._memory.clear()

    @message_handler
    async def on_publish_now(self, message: PublishNow, cancellation_token: CancellationToken) -> None:
        response = await self._generate_response(cancellation_token)
        self.publish_message(response)

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
