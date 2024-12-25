from autogen_core.components.models import LLMMessage
from autogen_core.models import ChatCompletionClient
from autogen_core.models import UserMessage

client = ChatCompletionClient.load_component(
    {
        "provider": "openai_model_client",
        "config": {
            "model": "gpt-4o"
        }
    }
)

# async def main():
#     print(await client.create([UserMessage(source="user", content="Hello")]))

# import asyncio

# asyncio.run(main())

print(client.dump_component().model_dump_json())