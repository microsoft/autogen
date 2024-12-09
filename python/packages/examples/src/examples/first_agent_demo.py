from dataclasses import dataclass

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentId, MessageContext
from autogen_core.components import DefaultTopicId, RoutedAgent, default_subscription, message_handler
from autogen_core.components.model_context import BufferedChatCompletionContext
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models import OpenAIChatCompletionClient


def get_model_client() -> OpenAIChatCompletionClient:
    "Mimic OpenAI API using Local LLM Server."
    return OpenAIChatCompletionClient(
        model="qwen2",  # Need to use one of the OpenAI models as a placeholder for now.
        api_key="NotRequiredSinceWeAreLocal",
        base_url="http://127.0.0.1:4000",
    )

@dataclass
class Message:
    content: str

@default_subscription
class Assistant(RoutedAgent):
    def __init__(self, name: str, model_client: ChatCompletionClient) -> None:
        super().__init__("An assistant agent.")
        self._model_client = model_client
        self.name = name
        self.count = 0
        self._system_messages = [
            SystemMessage(
                content=f"Your name is {name} and you are a part of a duo of comedians."
                "You laugh when you find the joke funny, else reply 'I need to go now'.",
            )
        ]
        self._model_context = BufferedChatCompletionContext(buffer_size=5)

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        self.count += 1
        await self._model_context.add_message(UserMessage(content=message.content, source="user"))
        result = await self._model_client.create(self._system_messages + await self._model_context.get_messages())

        print(f"\n{self.name}: {message.content}")

        if "I need to go".lower() in message.content.lower() or self.count > 2:
            return

        await self._model_context.add_message(AssistantMessage(content=result.content, source="assistant"))  # type: ignore
        await self.publish_message(Message(content=result.content), DefaultTopicId())  # type: ignore

if __name__=="__main__":
    ## 设置代理
    runtime = SingleThreadedAgentRuntime()

