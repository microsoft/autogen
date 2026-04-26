import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    streaming_assistant = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="You are a helpful assistant.",
        model_client_stream=True,  # Enable streaming tokens.
    )
    print("--- Streaming tokens as they are generated ---")
    async for message in streaming_assistant.run_stream(task="Name two cities in South America"):  # type: ignore
        print(message)
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
