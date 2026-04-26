"""
core_model_clients_example.py

Demonstrates usage of AutoGen model clients:
- OpenAIChatCompletionClient (basic call)
- Streaming tokens with create_stream()
- Structured output with Pydantic BaseModel
- Caching with DiskCacheStore
- Logging model calls
- Building an agent with a model client

To run:
    python core_model_clients_example.py

Note: Requires OPENAI_API_KEY in environment for OpenAI examples.
"""
import asyncio
import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

try:
    from pydantic import BaseModel
    from autogen_core import EVENT_LOGGER_NAME, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler, AgentId
    from autogen_core.models import UserMessage, SystemMessage, ChatCompletionClient
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_ext.cache_store.diskcache import DiskCacheStore
    from autogen_ext.models.cache import CHAT_CACHE_VALUE_TYPE, ChatCompletionCache
    from diskcache import Cache
except ImportError as e:
    print("Required packages not installed:", e)
    print("Please install autogen-core, autogen-ext, pydantic, and diskcache.")
    exit(1)

# --- Enable model call logging ---
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

async def basic_model_call():
    print("\n--- Basic Model Call ---")
    model_client = OpenAIChatCompletionClient(model="gpt-4", temperature=0.3)
    result = await model_client.create([UserMessage(content="What is the capital of France?", source="user")])
    print("Result:", result)
    await model_client.close()

async def streaming_tokens():
    print("\n--- Streaming Tokens ---")
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    messages = [UserMessage(content="Write a very short story about a dragon.", source="user")]
    stream = model_client.create_stream(messages=messages)
    print("Streamed responses:")
    async for chunk in stream:
        if isinstance(chunk, str):
            print(chunk, flush=True, end="")
        else:
            print("\n\n------------\n")
            print("The complete response:", flush=True)
            print(chunk.content, flush=True)
    await model_client.close()

# --- Structured output ---
class AgentResponse(BaseModel):
    thoughts: str
    response: Literal["happy", "sad", "neutral"]

async def structured_output():
    print("\n--- Structured Output ---")
    model_client = OpenAIChatCompletionClient(model="gpt-4o", response_format=AgentResponse)  # type: ignore
    messages = [UserMessage(content="I am happy.", source="user")]
    response = await model_client.create(messages=messages)
    print("Raw content:", response.content)
    parsed_response = AgentResponse.model_validate_json(response.content)
    print("Parsed thoughts:", parsed_response.thoughts)
    print("Parsed response:", parsed_response.response)
    await model_client.close()

async def caching_example():
    print("\n--- Caching Model Responses ---")
    with tempfile.TemporaryDirectory() as tmpdirname:
        openai_model_client = OpenAIChatCompletionClient(model="gpt-4o")
        cache_store = DiskCacheStore[CHAT_CACHE_VALUE_TYPE](Cache(tmpdirname))
        cache_client = ChatCompletionCache(openai_model_client, cache_store)
        response1 = await cache_client.create([UserMessage(content="Hello, how are you?", source="user")])
        print("First response:", response1)
        response2 = await cache_client.create([UserMessage(content="Hello, how are you?", source="user")])
        print("Cached response:", response2)
        await openai_model_client.close()
        await cache_client.close()

# --- Agent using a model client ---
@dataclass
class Message:
    content: str

class SimpleAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A simple agent")
        self._system_messages = [SystemMessage(content="You are a helpful AI assistant.")]
        self._model_client = model_client

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        user_message = UserMessage(content=message.content, source="user")
        response = await self._model_client.create(
            self._system_messages + [user_message], cancellation_token=ctx.cancellation_token
        )
        assert isinstance(response.content, str)
        return Message(content=response.content)

async def agent_with_model_client():
    print("\n--- Agent with Model Client ---")
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    runtime = SingleThreadedAgentRuntime()
    await SimpleAgent.register(
        runtime,
        "simple_agent",
        lambda: SimpleAgent(model_client=model_client),
    )
    runtime.start()
    message = Message("Hello, what are some fun things to do in Seattle?")
    response = await runtime.send_message(message, AgentId("simple_agent", "default"))
    print("Agent response:", response.content)
    await runtime.stop()
    await model_client.close()

async def main():
    await basic_model_call()
    await streaming_tokens()
    await structured_output()
    await caching_example()
    await agent_with_model_client()

if __name__ == "__main__":
    asyncio.run(main())
