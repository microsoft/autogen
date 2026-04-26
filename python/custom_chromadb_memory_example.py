"""
Custom Memory Store Example: ChromaDB Vector Memory with AssistantAgent

Demonstrates how to use ChromaDBVectorMemory (vector database) as a memory store for an agent.
- Stores user preferences as vector embeddings
- Retrieves relevant preferences via similarity search
- Integrates with AssistantAgent for context-aware responses

Requirements:
- autogen-agentchat, autogen-core, autogen-ext
- chromadb, sentence-transformers

Run: python custom_chromadb_memory_example.py
"""
import asyncio
import tempfile

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_ext.memory.chromadb import (
    ChromaDBVectorMemory,
    PersistentChromaDBVectorMemoryConfig,
    SentenceTransformerEmbeddingFunctionConfig,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Dummy weather tool for demonstration
def get_weather(city: str, units: str = "metric") -> str:
    if units == "metric":
        return f"The weather in {city} is 23 °C and Sunny."
    else:
        return f"The weather in {city} is 73 °F and Sunny."

def main():
    async def run():
        # Use a temporary directory for ChromaDB persistence
        with tempfile.TemporaryDirectory() as tmpdir:
            chroma_user_memory = ChromaDBVectorMemory(
                config=PersistentChromaDBVectorMemoryConfig(
                    collection_name="preferences",
                    persistence_path=tmpdir,  # Use the temp directory here
                    k=2,  # Return top k results
                    score_threshold=0.4,  # Minimum similarity score
                    embedding_function_config=SentenceTransformerEmbeddingFunctionConfig(
                        model_name="all-MiniLM-L6-v2"  # Use default model for testing
                    ),
                )
            )
            # Add user preferences to memory
            await chroma_user_memory.add(
                MemoryContent(
                    content="The weather should be in metric units",
                    mime_type=MemoryMimeType.TEXT,
                    metadata={"category": "preferences", "type": "units"},
                )
            )
            await chroma_user_memory.add(
                MemoryContent(
                    content="Meal recipe must be vegan",
                    mime_type=MemoryMimeType.TEXT,
                    metadata={"category": "preferences", "type": "dietary"},
                )
            )

            model_client = OpenAIChatCompletionClient(
                model="gpt-4o",
            )

            # Create assistant agent with ChromaDB memory
            assistant_agent = AssistantAgent(
                name="assistant_agent",
                model_client=model_client,
                tools=[get_weather],
                memory=[chroma_user_memory],
            )

            print("\n--- User: What is the weather in New York? ---\n")
            stream = assistant_agent.run_stream(task="What is the weather in New York?")
            await Console(stream)

            print("\n--- User: Suggest a vegan meal recipe ---\n")
            stream2 = assistant_agent.run_stream(task="Suggest a vegan meal recipe.")
            await Console(stream2)

            # Show how to serialize memory
            print("\nSerialized ChromaDBVectorMemory config:")
            print(chroma_user_memory.dump_component().model_dump_json())

            await model_client.close()
            await chroma_user_memory.close()

    asyncio.run(run())

if __name__ == "__main__":
    main()
