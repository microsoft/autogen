from typing import Any, Callable, List, Mapping

import openai
from openai import AsyncAssistantEventHandler
from openai.types.beta import AssistantResponseFormatParam

from agnext.chat.agents.base import BaseChatAgent
from agnext.chat.types import Reset, RespondNow, ResponseFormat, TextMessage
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import AgentRuntime, CancellationToken


class OpenAIAssistantAgent(BaseChatAgent, TypeRoutedAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        client: openai.AsyncClient,
        assistant_id: str,
        thread_id: str,
        assistant_event_handler_factory: Callable[[], AsyncAssistantEventHandler] | None = None,
    ) -> None:
        super().__init__(name, description, runtime)
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id
        self._assistant_event_handler_factory = assistant_event_handler_factory

    @message_handler()
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken) -> None:
        # Save the message to the thread.
        _ = await self._client.beta.threads.messages.create(
            thread_id=self._thread_id,
            content=message.content,
            role="user",
            metadata={"sender": message.source},
        )

    @message_handler()
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
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
        # Handle response format.
        if message.response_format == ResponseFormat.json_object:
            response_format = AssistantResponseFormatParam(type="json_object")
        else:
            response_format = AssistantResponseFormatParam(type="text")

        if self._assistant_event_handler_factory is not None:
            # Use event handler and streaming mode if available.
            async with self._client.beta.threads.runs.stream(
                thread_id=self._thread_id,
                assistant_id=self._assistant_id,
                event_handler=self._assistant_event_handler_factory(),
                response_format=response_format,
            ) as stream:
                run = await stream.get_final_run()
        else:
            # Use blocking mode.
            run = await self._client.beta.threads.runs.create(
                thread_id=self._thread_id,
                assistant_id=self._assistant_id,
                response_format=response_format,
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
        return TextMessage(content=text_content[0].text.value, source=self.name)

    def save_state(self) -> Mapping[str, Any]:
        return {
            "description": self.description,
            "assistant_id": self._assistant_id,
            "thread_id": self._thread_id,
        }

    def load_state(self, state: Mapping[str, Any]) -> None:
        self._description = state["description"]
        self._assistant_id = state["assistant_id"]
        self._thread_id = state["thread_id"]
