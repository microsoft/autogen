from typing import Literal

import openai
from agnext.components import (
    TypeRoutedAgent,
    message_handler,
)
from agnext.core import CancellationToken
from messages import ArticleCreated, GraphicDesignCreated


class GraphicDesignerAgent(TypeRoutedAgent):
    def __init__(
        self,
        client: openai.AsyncClient,
        model: Literal["dall-e-2", "dall-e-3"] = "dall-e-3",
    ):
        super().__init__("")
        self._client = client
        self._model = model

    @message_handler
    async def handle_user_chat_input(self, message: ArticleCreated, cancellation_token: CancellationToken) -> None:
        response = await self._client.images.generate(
            model=self._model, prompt=message.article, response_format="b64_json"
        )
        assert len(response.data) > 0 and response.data[0].b64_json is not None
        image_base64 = response.data[0].b64_json
        image_uri = f"data:image/png;base64,{image_base64}"

        await self.publish_message(GraphicDesignCreated(user_id=message.user_id, image_uri=image_uri))
