import openai

from agnext.agent_components.type_routed_agent import message_handler
from agnext.chat.agents.base import BaseChatAgent
from agnext.core.agent_runtime import AgentRuntime
from agnext.core.cancellation_token import CancellationToken

from ..messages import ChatMessage


class OpenAIAssistantAgent(BaseChatAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        client: openai.AsyncClient,
        assistant_id: str,
        thread_id: str,
    ) -> None:
        super().__init__(name, description, runtime)
        self._client = client
        self._assistant_id = assistant_id
        self._thread_id = thread_id
        self._current_session_window_length = 0

    # TODO: use require_response
    @message_handler(ChatMessage)
    async def on_chat_message_with_cancellation(
        self, message: ChatMessage, require_response: bool, cancellation_token: CancellationToken
    ) -> ChatMessage | None:
        print("---------------")
        print(f"{self.name} received message from {message.sender}: {message.body}")
        print("---------------")
        if message.reset:
            # Reset the current session window.
            self._current_session_window_length = 0

        # Save the message to the thread.
        _ = await self._client.beta.threads.messages.create(
            thread_id=self._thread_id,
            content=message.body,
            role="user",
            metadata={"sender": message.sender},
        )
        self._current_session_window_length += 1

        # If the message is a save_message_only message, return early.
        if message.save_message_only:
            return ChatMessage(body="OK", sender=self.name)

        # Create a run and wait until it finishes.
        run = await self._client.beta.threads.runs.create_and_poll(
            thread_id=self._thread_id,
            assistant_id=self._assistant_id,
            truncation_strategy={
                "type": "last_messages",
                "last_messages": self._current_session_window_length,
            },
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
        return ChatMessage(body=text_content[0].text.value, sender=self.name)
