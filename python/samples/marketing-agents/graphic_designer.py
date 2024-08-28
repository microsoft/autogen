import logging
from typing import Literal

import openai
from agnext.base import MessageContext
from agnext.components import (
    DefaultTopicId,
    RoutedAgent,
    message_handler,
)
from messages import ArticleCreated, GraphicDesignCreated


class GraphicDesignerAgent(RoutedAgent):
    def __init__(
        self,
        client: openai.AsyncClient,
        model: Literal["dall-e-2", "dall-e-3"] = "dall-e-3",
    ):
        super().__init__("")
        self._client = client
        self._model = model

    @message_handler
    async def handle_user_chat_input(self, message: ArticleCreated, ctx: MessageContext) -> None:
        logger = logging.getLogger("graphic_designer")
        try:
            logger.info(f"Asking model to generate an image for the article '{message.article}'.")
            response = await self._client.images.generate(
                model=self._model, prompt=message.article, response_format="url"
            )
            logger.info(f"Image response: '{response.data[0]}'")
            assert len(response.data) > 0 and response.data[0].url is not None
            image_uri = response.data[0].url
            logger.info(f"Generated image for article. Got response: '{image_uri}'")

            await self.publish_message(
                GraphicDesignCreated(UserId=message.UserId, imageUri=image_uri), topic_id=DefaultTopicId()
            )
        except Exception as e:
            logger.error(f"Failed to generate image for article. Error: {e}")
