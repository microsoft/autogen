import asyncio
from dataclasses import dataclass
from typing import Any, List

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    OpenAI,
    SystemMessage,
    UserMessage,
)
from agnext.core import AgentId, CancellationToken
from agnext.core.intervention import DefaultInterventionHandler


@dataclass
class Message:
    source: str
    content: str


@dataclass
class Termination:
    pass


class ChatCompletionAgent(TypeRoutedAgent):
    """An agent that uses a chat completion model to respond to messages.
    It keeps a memory of the conversation and uses it to generate responses.
    It publishes a termination message when the termination word is mentioned."""

    def __init__(
        self,
        description: str,
        system_messages: List[SystemMessage],
        model_client: ChatCompletionClient,
        termination_word: str,
    ) -> None:
        super().__init__(description)
        self._system_messages = system_messages
        self._model_client = model_client
        self._memory: List[Message] = []
        self._termination_word = termination_word

    @message_handler
    async def handle_message(self, message: Message, cancellation_token: CancellationToken) -> None:
        self._memory.append(message)
        if self._termination_word in message.content:
            self.publish_message(Termination())
            return
        llm_messages: List[LLMMessage] = []
        for m in self._memory[-10:]:
            if m.source == self.metadata["name"]:
                llm_messages.append(AssistantMessage(content=m.content, source=self.metadata["name"]))
            else:
                llm_messages.append(UserMessage(content=m.content, source=m.source))
        response = await self._model_client.create(self._system_messages + llm_messages)
        assert isinstance(response.content, str)
        self.publish_message(Message(content=response.content, source=self.metadata["name"]))


class TerminationHandler(DefaultInterventionHandler):
    """A handler that listens for termination messages."""

    def __init__(self) -> None:
        self._terminated = False

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any:
        if isinstance(message, Termination):
            self._terminated = True
        return message

    @property
    def terminated(self) -> bool:
        return self._terminated


async def main() -> None:
    # Create the termination handler.
    termination_handler = TerminationHandler()

    # Create the runtime with the termination handler.
    runtime = SingleThreadedAgentRuntime(intervention_handler=termination_handler)

    # Register the agents.
    jack = runtime.register_and_get(
        "Jack",
        lambda: ChatCompletionAgent(
            description="Jack a comedian",
            model_client=OpenAI(model="gpt-3.5-turbo"),
            system_messages=[
                SystemMessage("You are a comedian likes to make jokes. " "When you are done talking, say 'TERMINATE'.")
            ],
            termination_word="TERMINATE",
        ),
    )
    runtime.register_and_get(
        "Cathy",
        lambda: ChatCompletionAgent(
            description="Cathy a poet",
            model_client=OpenAI(model="gpt-3.5-turbo"),
            system_messages=[
                SystemMessage("You are a poet likes to write poems. " "When you are done talking, say 'TERMINATE'.")
            ],
            termination_word="TERMINATE",
        ),
    )

    # Send a message to Jack to start the conversation.
    message = Message(content="Can you tell me something fun about SF?", source="User")
    runtime.send_message(message, jack)

    # Process messages until termination.
    while not termination_handler.terminated:
        await runtime.process_next()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
