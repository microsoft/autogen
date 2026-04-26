"""
core_model_context_example.py

Demonstrates model context usage in AutoGen:
- BufferedChatCompletionContext for message history
- Agent that remembers previous conversation
- Integration with model client and runtime

To run:
    python core_model_context_example.py

Note: Requires OPENAI_API_KEY in environment for OpenAI examples.
"""
import asyncio
from dataclasses import dataclass

try:
    from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
    from autogen_core.model_context import BufferedChatCompletionContext
    from autogen_core.models import AssistantMessage, ChatCompletionClient, SystemMessage, UserMessage
    from autogen_ext.models.openai import OpenAIChatCompletionClient
except ImportError as e:
    print("Required packages not installed:", e)
    print("Please install autogen-core and autogen-ext.")
    exit(1)

@dataclass
class Message:
    content: str

class SimpleAgentWithContext(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A simple agent")
        self._system_messages = [SystemMessage(content="You are a helpful AI assistant.")]
        self._model_client = model_client
        self._model_context = BufferedChatCompletionContext(buffer_size=5)

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        user_message = UserMessage(content=message.content, source="user")
        await self._model_context.add_message(user_message)
        response = await self._model_client.create(
            self._system_messages + (await self._model_context.get_messages()),
            cancellation_token=ctx.cancellation_token,
        )
        assert isinstance(response.content, str)
        await self._model_context.add_message(AssistantMessage(content=response.content, source=self.metadata["type"]))
        return Message(content=response.content)

async def main():
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    runtime = SingleThreadedAgentRuntime()
    await SimpleAgentWithContext.register(
        runtime,
        "simple_agent_context",
        lambda: SimpleAgentWithContext(model_client=model_client),
    )
    runtime.start()
    agent_id = AgentId("simple_agent_context", "default")

    # First question
    message = Message("Hello, what are some fun things to do in Seattle?")
    print(f"Question: {message.content}")
    response = await runtime.send_message(message, agent_id)
    print(f"Response: {response.content}")
    print("-----")

    # Second question
    message = Message("What was the first thing you mentioned?")
    print(f"Question: {message.content}")
    response = await runtime.send_message(message, agent_id)
    print(f"Response: {response.content}")

    await runtime.stop()
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
