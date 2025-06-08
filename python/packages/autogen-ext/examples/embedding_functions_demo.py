#!/usr/bin/env python3
"""
Demonstration of ChromaDB embedding function configurations in AutoGen.

This example shows how to use different embedding functions with ChromaDBVectorMemory:
1. Default embedding function
2. Custom SentenceTransformer model
3. OpenAI embeddings (requires API key)
4. Custom embedding function

Run this script to see the different embedding functions in action.
"""

import asyncio
import os
import tempfile
from pathlib import Path

from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_ext.memory.chromadb import (
    ChromaDBVectorMemory,
    DefaultEmbeddingFunctionConfig,
    OpenAIEmbeddingFunctionConfig,
    PersistentChromaDBVectorMemoryConfig,
    SentenceTransformerEmbeddingFunctionConfig,
    CustomEmbeddingFunctionConfig,
)


async def demo_default_embedding():
    """Demonstrate default embedding function."""
    print("🔹 Demo 1: Default Embedding Function")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = PersistentChromaDBVectorMemoryConfig(
            collection_name="default_demo",
            persistence_path=str(Path(tmp_dir) / "default_db"),
            embedding_function_config=DefaultEmbeddingFunctionConfig()
        )
        
        memory = ChromaDBVectorMemory(config=config)
        await memory.clear()
        
        # Add some content
        await memory.add(MemoryContent(
            content="The Eiffel Tower is a famous landmark in Paris, France.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "landmarks", "city": "Paris"}
        ))
        
        await memory.add(MemoryContent(
            content="The Statue of Liberty is located in New York Harbor.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "landmarks", "city": "New York"}
        ))
        
        # Query the memory
        results = await memory.query("famous tower in France")
        print(f"   Query: 'famous tower in France'")
        print(f"   Results: {len(results.results)} found")
        for i, result in enumerate(results.results):
            score = result.metadata.get("score", 0) if result.metadata else 0
            print(f"   {i+1}. {result.content} (score: {score:.3f})")
        
        await memory.close()
        print("   ✅ Default embedding function demo completed\n")

        # Small delay to ensure file handles are released on Windows
        import time
        time.sleep(0.1)


async def demo_sentence_transformer_embedding():
    """Demonstrate SentenceTransformer embedding function."""
    print("🔹 Demo 2: SentenceTransformer Embedding Function")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = PersistentChromaDBVectorMemoryConfig(
            collection_name="sentence_transformer_demo",
            persistence_path=str(Path(tmp_dir) / "st_db"),
            embedding_function_config=SentenceTransformerEmbeddingFunctionConfig(
                model_name="all-MiniLM-L6-v2"  # Using the default model for demo
            )
        )
        
        memory = ChromaDBVectorMemory(config=config)
        await memory.clear()
        
        # Add some content
        await memory.add(MemoryContent(
            content="Machine learning is a subset of artificial intelligence.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "technology", "topic": "AI"}
        ))
        
        await memory.add(MemoryContent(
            content="Deep learning uses neural networks with multiple layers.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "technology", "topic": "AI"}
        ))
        
        # Query the memory
        results = await memory.query("neural networks and AI")
        print(f"   Query: 'neural networks and AI'")
        print(f"   Results: {len(results.results)} found")
        for i, result in enumerate(results.results):
            score = result.metadata.get("score", 0) if result.metadata else 0
            print(f"   {i+1}. {result.content} (score: {score:.3f})")
        
        await memory.close()
        print("   ✅ SentenceTransformer embedding function demo completed\n")

        # Small delay to ensure file handles are released on Windows
        import time
        time.sleep(0.1)


async def demo_openai_embedding():
    """Demonstrate OpenAI embedding function (requires API key)."""
    print("🔹 Demo 3: OpenAI Embedding Function")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("   ⚠️  Skipping OpenAI demo - OPENAI_API_KEY environment variable not set")
        print("   To run this demo, set your OpenAI API key: export OPENAI_API_KEY=your_key_here\n")
        return
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = PersistentChromaDBVectorMemoryConfig(
            collection_name="openai_demo",
            persistence_path=str(Path(tmp_dir) / "openai_db"),
            embedding_function_config=OpenAIEmbeddingFunctionConfig(
                api_key=api_key,
                model_name="text-embedding-ada-002"
            )
        )
        
        memory = ChromaDBVectorMemory(config=config)
        await memory.clear()
        
        # Add some content
        await memory.add(MemoryContent(
            content="Climate change is affecting global weather patterns.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "environment", "topic": "climate"}
        ))
        
        await memory.add(MemoryContent(
            content="Renewable energy sources include solar and wind power.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "environment", "topic": "energy"}
        ))
        
        # Query the memory
        results = await memory.query("sustainable energy solutions")
        print(f"   Query: 'sustainable energy solutions'")
        print(f"   Results: {len(results.results)} found")
        for i, result in enumerate(results.results):
            score = result.metadata.get("score", 0) if result.metadata else 0
            print(f"   {i+1}. {result.content} (score: {score:.3f})")
        
        await memory.close()
        print("   ✅ OpenAI embedding function demo completed\n")

        # Small delay to ensure file handles are released on Windows
        import time
        time.sleep(0.1)


async def demo_custom_embedding():
    """Demonstrate custom embedding function."""
    print("🔹 Demo 4: Custom Embedding Function")
    
    def create_custom_embedding_function():
        """Create a custom embedding function (using default for demo)."""
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            # In a real scenario, you would implement your own embedding logic here
            return DefaultEmbeddingFunction()
        except ImportError:
            raise ImportError("ChromaDB not available for custom embedding function")
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        config = PersistentChromaDBVectorMemoryConfig(
            collection_name="custom_demo",
            persistence_path=str(Path(tmp_dir) / "custom_db"),
            embedding_function_config=CustomEmbeddingFunctionConfig(
                function=create_custom_embedding_function,
                params={}
            )
        )
        
        memory = ChromaDBVectorMemory(config=config)
        await memory.clear()
        
        # Add some content
        await memory.add(MemoryContent(
            content="Custom embedding functions allow for specialized use cases.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "technical", "topic": "embeddings"}
        ))
        
        await memory.add(MemoryContent(
            content="You can implement domain-specific embedding logic.",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "technical", "topic": "customization"}
        ))
        
        # Query the memory
        results = await memory.query("specialized embedding implementations")
        print(f"   Query: 'specialized embedding implementations'")
        print(f"   Results: {len(results.results)} found")
        for i, result in enumerate(results.results):
            score = result.metadata.get("score", 0) if result.metadata else 0
            print(f"   {i+1}. {result.content} (score: {score:.3f})")
        
        await memory.close()
        print("   ✅ Custom embedding function demo completed\n")

        # Small delay to ensure file handles are released on Windows
        import time
        time.sleep(0.1)


async def main():
    """Run all embedding function demonstrations."""
    print("🚀 ChromaDB Embedding Functions Demo")
    print("=" * 50)
    
    try:
        await demo_default_embedding()
        await demo_sentence_transformer_embedding()
        await demo_openai_embedding()
        await demo_custom_embedding()
        
        print("🎉 All demos completed successfully!")
        print("\nKey takeaways:")
        print("• Default embedding function works out of the box")
        print("• SentenceTransformer allows custom models")
        print("• OpenAI embeddings provide high-quality results (requires API key)")
        print("• Custom functions enable specialized embedding logic")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
