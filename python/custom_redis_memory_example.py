"""
Custom Memory Store Example: RedisMemory with AssistantAgent

Demonstrates how to use RedisMemory (vector database) as a memory store for an agent.
- Stores user preferences in Redis
- Retrieves relevant preferences via similarity search
- Integrates with AssistantAgent for context-aware responses

Requirements:
- autogen-agentchat, autogen-core, autogen-ext
- redis-py, running Redis instance (see RedisMemory docs for setup)

Run: python custom_redis_memory_example.py
"""
import asyncio
from logging import WARNING, getLogger

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_ext.memory.redis import RedisMemory, RedisMemoryConfig
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Dummy weather tool for demonstration
def get_weather(city: str, units: str = "metric") -> str:
    if units == "metric":
        return f"The weather in {city} is 23 °C and Sunny."
    else:
        return f"The weather in {city} is 73 °F and Sunny."

def main():
    async def run():
        logger = getLogger()
        logger.setLevel(WARNING)

        # Initialize Redis memory (requires running Redis instance)
        redis_memory = RedisMemory(
            config=RedisMemoryConfig(
                redis_url="redis://localhost:6379",
                index_name="chat_history",
                prefix="memory",
            )
        )

        # Add user preferences to memory
        await redis_memory.add(
            MemoryContent(
                content="The weather should be in metric units",
                mime_type=MemoryMimeType.TEXT,
                metadata={"category": "preferences", "type": "units"},
            )
        )
        await redis_memory.add(
            MemoryContent(
                content="Meal recipe must be vegan",
                mime_type=MemoryMimeType.TEXT,
                metadata={"category": "preferences", "type": "dietary"},
            )
        )

        model_client = OpenAIChatCompletionClient(
            model="gpt-4o",
        )

        # Create assistant agent with Redis memory
        assistant_agent = AssistantAgent(
            name="assistant_agent",
            model_client=model_client,
            tools=[get_weather],
            memory=[redis_memory],
        )

        print("\n--- User: What is the weather in New York? ---\n")
        stream = assistant_agent.run_stream(task="What is the weather in New York?")
        await Console(stream)

        print("\n--- User: Suggest a vegan meal recipe ---\n")
        stream2 = assistant_agent.run_stream(task="Suggest a vegan meal recipe.")
        await Console(stream2)

        # Show how to serialize memory
        print("\nSerialized RedisMemory config:")
        print(redis_memory.dump_component().model_dump_json())

        await model_client.close()
        await redis_memory.close()

    asyncio.run(run())

if __name__ == "__main__":
    main()
