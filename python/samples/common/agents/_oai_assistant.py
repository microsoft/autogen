from typing import Any, Callable, List, Mapping

import openai
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import CancellationToken
from openai import AsyncAssistantEventHandler
from openai.types import ResponseFormatJSONObject, ResponseFormatText  # type: ignore

from ..types import PublishNow, Reset, RespondNow, ResponseFormat, TextMessage


class OpenAIAssistantAgent(TypeRoutedAgent):
    """An agent implementation that uses the OpenAI Assistant API to generate
    responses.

    Args:
        description (str): The description of the agent.
        client (openai.AsyncClient): The client to use for the OpenAI API.
        assistant_id (str): The assistant ID to use for the OpenAI API.
        thread_id (str): The thread ID to use for the OpenAI API.
        assistant_event_handler_factory (Callable[[], AsyncAssistantEventHandler], optional):
            A factory function to create an async assistant event handler. Defaults to None.
            If provided, the agent will use the streaming mode with the event handler.
            If not provided, the agent will use the blocking mode to generate responses.
    """

    def __init__(
        self,
        description: str,
        client: openai.AsyncClient,
        assistant_id: str,
        thread_id: str,
        assistant_event_handler_factory: (Callable[[], AsyncAssistantEventHandler] | None) = None,
    ) -> None:
        super().__init__(description)
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id
        self._assistant_event_handler_factory = assistant_event_handler_factory

    @message_handler()
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        """Handle a text message. This method adds the message to the thread."""
        # Save the message to the thread.
        _ = await self._client.beta.threads.messages.create(
            thread_id=self._thread_id,
            content=message.content,
            role="user",
            metadata={"sender": message.source},
        )

    @message_handler()
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        """Handle a reset message. This method deletes all messages in the thread."""
        # Get all messages in this thread.
        all_msgs: List[str] = []
        while True:
            if not all_msgs:
                msgs = await self._client.beta.threads.messages.list(self._thread_id)
            else:
                msgs = await self._client.beta.threads.messages.list(self._thread_id, after=all_msgs[-1])
            for msg in msgs.data:
                all_msgs.append(msg.id)
            if not msgs.has_next_page():
                break
        # Delete all the messages.
        for msg_id in all_msgs:
            status = await self._client.beta.threads.messages.delete(message_id=msg_id, thread_id=self._thread_id)
            assert status.deleted is True

    @message_handler()
    async def on_respond_now(self, message: RespondNow, cancellation_token: CancellationToken) -> TextMessage:
        """Handle a respond now message. This method generates a response and returns it to the sender."""
        return await self._generate_response(message.response_format, cancellation_token)

    @message_handler()
    async def on_publish_now(self, message: PublishNow, cancellation_token: CancellationToken) -> None:
        """Handle a publish now message. This method generates a response and publishes it."""
        response = await self._generate_response(message.response_format, cancellation_token)
        await self.publish_message(response)

    async def _generate_response(
        self,
        requested_response_format: ResponseFormat,
        cancellation_token: CancellationToken,
    ) -> TextMessage:
        # Handle response format.
        if requested_response_format == ResponseFormat.json_object:
            response_format = ResponseFormatJSONObject(type="json_object")  # type: ignore
        else:
            response_format = ResponseFormatText(type="text")  # type: ignore

        if self._assistant_event_handler_factory is not None:
            # Use event handler and streaming mode if available.
            async with self._client.beta.threads.runs.stream(
                thread_id=self._thread_id,
                assistant_id=self._assistant_id,
                event_handler=self._assistant_event_handler_factory(),
                response_format=response_format,  # type: ignore
            ) as stream:
                run = await stream.get_final_run()
        else:
            # Use blocking mode.
            run = await self._client.beta.threads.runs.create(
                thread_id=self._thread_id,
                assistant_id=self._assistant_id,
                response_format=response_format,  # type: ignore
            )

        if run.status != "completed":
            # TODO: handle other statuses.
            raise ValueError(f"Run did not complete successfully: {run}")

        # Get the last message from the run.
        response = await self._client.beta.threads.messages.list(self._thread_id, run_id=run.id, order="desc", limit=1)
        last_message_content = response.data[0].content

        # TODO: handle array of content.
        text_content = [content for content in last_message_content if content.type == "text"]
        if not text_content:
            raise ValueError(f"Expected text content in the last message: {last_message_content}")

        # TODO: handle multiple text content.
        return TextMessage(content=text_content[0].text.value, source=self.metadata["name"])

    def save_state(self) -> Mapping[str, Any]:
        return {
            "assistant_id": self._assistant_id,
            "thread_id": self._thread_id,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._assistant_id = state["assistant_id"]
        self._thread_id = state["thread_id"]
