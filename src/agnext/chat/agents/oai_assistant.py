import openai

from agnext.agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from agnext.chat.agents.base import BaseChatAgent
from agnext.chat.types import Reset, RespondNow, TextMessage
from agnext.core.agent_runtime import AgentRuntime
from agnext.core.cancellation_token import CancellationToken


class OpenAIAssistantAgent(BaseChatAgent, TypeRoutedAgent):
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
    @message_handler(TextMessage)
    async def on_chat_message_with_cancellation(
        self, message: TextMessage, require_response: bool, cancellation_token: CancellationToken
    ) -> None:
        print("---------------")
        print(f"{self.name} received message from {message.source}: {message.content}")
        print("---------------")

        # Save the message to the thread.
        _ = await self._client.beta.threads.messages.create(
            thread_id=self._thread_id,
            content=message.content,
            role="user",
            metadata={"sender": message.source},
        )
        self._current_session_window_length += 1

        if require_response:
            # TODO ?
            ...

    @message_handler(Reset)
    async def on_reset(self, message: Reset, require_response: bool, cancellation_token: CancellationToken) -> None:
        # Reset the current session window.
        self._current_session_window_length = 0

    @message_handler(RespondNow)
    async def on_respond_now(
        self, message: RespondNow, require_response: bool, cancellation_token: CancellationToken
    ) -> TextMessage | None:
        if not require_response:
            return None

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
        return TextMessage(content=text_content[0].text.value, source=self.name)
