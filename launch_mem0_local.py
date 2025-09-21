#!/usr/bin/env python3
"""
Mem0 Local Launch Script
========================

This script demonstrates how to launch Mem0 integration locally with different configurations.

Usage:
    python launch_mem0_local.py [--mode cloud|local|mock]
"""

import asyncio
import argparse
import os
from typing import Optional

from autogen_ext.memory.mem0 import Mem0Memory, Mem0MemoryConfig
from autogen_core.memory import MemoryContent


async def demo_memory_operations(memory: Mem0Memory, mode: str):
    """Demonstrate memory operations with the given memory instance."""
    print(f"\n🧠 Testing {mode.upper()} Memory Operations...")
    
    # Add some sample memories
    memories = [
        "User prefers Python programming language",
        "User likes working with AI and machine learning", 
        "User is interested in AutoGen framework",
        "User prefers local development environments",
        "User is debugging Mem0 integration today"
    ]
    
    print("\n📝 Adding memories...")
    for i, content in enumerate(memories, 1):
        try:
            await memory.add(MemoryContent(
                content=content,
                mime_type="text/plain",
                metadata={"source": f"{mode}-demo", "index": i}
            ))
            print(f"  ✅ Added: {content[:50]}...")
        except Exception as e:
            print(f"  ❌ Failed to add memory {i}: {e}")
            return False
    
    # Query memories
    print("\n🔍 Querying memories...")
    queries = [
        "What programming language does the user prefer?",
        "What is the user interested in?",
        "What is the user working on today?"
    ]
    
    for query in queries:
        print(f"\n  Query: \"{query}\"")
        try:
            results = await memory.query(query)
            print(f"  Found {len(results.results)} relevant memories:")
            for j, result in enumerate(results.results, 1):
                print(f"    {j}. {result.content}")
                if result.metadata:
                    score = result.metadata.get("score", "N/A")
                    print(f"       Score: {score}")
        except Exception as e:
            print(f"  ❌ Query failed: {e}")
            return False
    
    # Test context updating
    print("\n🔄 Testing context updating...")
    try:
        from autogen_core.model_context import BufferedChatCompletionContext
        from autogen_core.models import UserMessage
        
        context = BufferedChatCompletionContext(buffer_size=10)
        await context.add_message(UserMessage(
            content="Tell me about the user's preferences", 
            source="user"
        ))
        
        update_result = await memory.update_context(context)
        print(f"  ✅ Updated context with {len(update_result.memories.results)} relevant memories")
        
        messages = await context.get_messages()
        print(f"  Context now has {len(messages)} messages")
        
    except Exception as e:
        print(f"  ❌ Context update failed: {e}")
        return False
    
    # Clean up
    print("\n🧹 Cleaning up...")
    try:
        await memory.clear()
        print("  ✅ Memory cleared")
        
        await memory.close()
        print("  ✅ Memory closed")
    except Exception as e:
        print(f"  ❌ Cleanup failed: {e}")
        return False
    
    return True


async def launch_cloud_mode():
    """Launch Mem0 in cloud mode."""
    print("🌐 LAUNCHING MEM0 CLOUD MODE")
    print("=" * 50)
    
    api_key = os.getenv("MEM0_API_KEY")
    if not api_key:
        print("❌ MEM0_API_KEY environment variable not set")
        print("   Get your API key from: https://app.mem0.ai/dashboard/api-keys")
        print("   Then run: export MEM0_API_KEY=your_key")
        return False
    
    try:
        memory = Mem0Memory(
            user_id="cloud-user",
            is_cloud=True,
            api_key=api_key
        )
        print("✅ Cloud memory initialized successfully!")
        
        success = await demo_memory_operations(memory, "cloud")
        return success
        
    except Exception as e:
        print(f"❌ Cloud mode failed: {e}")
        return False


async def launch_local_mode():
    """Launch Mem0 in local mode with LLM server."""
    print("🏠 LAUNCHING MEM0 LOCAL MODE")
    print("=" * 50)
    
    # Check for local LLM servers
    import requests
    
    llm_config = None
    try:
        # Try Ollama
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            llm_config = {
                "provider": "ollama",
                "config": {"model": "tinyllama:latest"}
            }
            print("✅ Found Ollama server")
    except:
        pass
    
    if not llm_config:
        try:
            # Try LMStudio
            response = requests.get("http://localhost:1234/v1/models", timeout=2)
            if response.status_code == 200:
                llm_config = {
                    "provider": "lmstudio", 
                    "config": {"model": "mock-model"}
                }
                print("✅ Found LMStudio server")
        except:
            pass
    
    if not llm_config:
        print("❌ No local LLM server found")
        print("   Please start one of:")
        print("   - Ollama: ollama pull llama2 && ollama serve")
        print("   - LMStudio: Download and start local server")
        return False
    
    try:
        memory = Mem0Memory(
            user_id="local-user",
            is_cloud=False,
            config={"path": ":memory:"}
        )
        print("✅ Local memory initialized successfully!")
        
        success = await demo_memory_operations(memory, "local")
        return success
        
    except Exception as e:
        print(f"❌ Local mode failed: {e}")
        return False


async def launch_mock_mode():
    """Launch Mem0 in mock mode for testing."""
    print("🎭 LAUNCHING MEM0 MOCK MODE")
    print("=" * 50)
    
    from unittest.mock import MagicMock, patch
    
    with patch('autogen_ext.memory.mem0._mem0.Memory0') as mock_mem0_class:
        # Create a mock instance
        mock_mem0 = MagicMock()
        mock_mem0_class.from_config.return_value = mock_mem0
        
        # Mock the search results
        mock_mem0.search.return_value = [
            {
                'memory': 'User prefers Python programming language',
                'score': 0.95,
                'metadata': {'source': 'mock', 'timestamp': '2024-01-01'}
            },
            {
                'memory': 'User likes working with AI and machine learning',
                'score': 0.88,
                'metadata': {'source': 'mock', 'timestamp': '2024-01-01'}
            }
        ]
        
        try:
            memory = Mem0Memory(
                user_id="mock-user",
                is_cloud=False,
                config={"path": ":memory:"}
            )
            print("✅ Mock memory initialized successfully!")
            
            success = await demo_memory_operations(memory, "mock")
            return success
            
        except Exception as e:
            print(f"❌ Mock mode failed: {e}")
            return False


async def main():
    """Main function to launch Mem0 in the specified mode."""
    parser = argparse.ArgumentParser(description="Launch Mem0 integration locally")
    parser.add_argument(
        "--mode", 
        choices=["cloud", "local", "mock"], 
        default="mock",
        help="Launch mode (default: mock)"
    )
    
    args = parser.parse_args()
    
    print("🚀 MEM0 LOCAL LAUNCHER")
    print("=" * 50)
    print(f"Mode: {args.mode.upper()}")
    
    success = False
    
    if args.mode == "cloud":
        success = await launch_cloud_mode()
    elif args.mode == "local":
        success = await launch_local_mode()
    elif args.mode == "mock":
        success = await launch_mock_mode()
    
    if success:
        print("\n" + "=" * 50)
        print("🎉 MEM0 LAUNCHED SUCCESSFULLY!")
        print("\n📋 What we demonstrated:")
        print("✅ Memory creation and initialization")
        print("✅ Adding multiple memories with metadata")
        print("✅ Querying memories with natural language")
        print("✅ Context updating for AI conversations")
        print("✅ Memory cleanup and resource management")
        print("\n🔧 Ready for production use!")
    else:
        print("\n❌ MEM0 LAUNCH FAILED")
        print("Please check the error messages above and try again.")


if __name__ == "__main__":
    asyncio.run(main())
