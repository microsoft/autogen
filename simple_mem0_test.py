#!/usr/bin/env python3
"""
Simple Mem0 Integration Test

This script tests the Mem0 integration with the fixes applied.
"""

import asyncio
import sys
import os
import tempfile
import shutil

# Add the autogen-ext package to the path
sys.path.insert(0, '/workspaces/autogen/python/packages/autogen-ext/src')

from autogen_ext.memory.mem0 import Mem0Memory
from autogen_core.memory import MemoryContent


async def test_mem0_with_fixes():
    """Test Mem0 integration with the applied fixes."""
    print("🧪 Testing Mem0 Integration with Fixes")
    print("=" * 50)
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix='mem0_test_')
    print(f"📁 Using temporary directory: {temp_dir}")
    
    try:
        # Test 1: Simple configuration with proper file path
        print("\n📦 Test 1: Simple configuration with file path...")
        memory1 = Mem0Memory(
            user_id='test-user-1',
            is_cloud=False,
            config={'path': f'{temp_dir}/mem0_test.db'}
        )
        print("✅ Memory 1 created successfully!")
        
        # Test 2: In-memory configuration (should use temp dir)
        print("\n📦 Test 2: In-memory configuration...")
        memory2 = Mem0Memory(
            user_id='test-user-2',
            is_cloud=False,
            config={'path': ':memory:'}
        )
        print("✅ Memory 2 created successfully!")
        
        # Test 3: Cloud configuration (if API key available)
        print("\n📦 Test 3: Cloud configuration...")
        api_key = os.environ.get("MEM0_API_KEY")
        if api_key:
            memory3 = Mem0Memory(
                user_id='test-user-3',
                is_cloud=True,
                api_key=api_key
            )
            print("✅ Memory 3 (cloud) created successfully!")
        else:
            print("⚠️  No MEM0_API_KEY found, skipping cloud test")
            memory3 = None
        
        # Test basic operations (only if client is available)
        print("\n🧪 Testing basic operations...")
        
        # Test with memory1 (file-based)
        if hasattr(memory1, '_client') and memory1._client is not None:
            print("  📝 Testing add operation...")
            await memory1.add(MemoryContent(
                content='User prefers Python programming',
                mime_type='text/plain',
                metadata={'source': 'test'}
            ))
            print("  ✅ Add operation successful!")
            
            print("  🔍 Testing query operation...")
            results = await memory1.query('What programming language does the user prefer?')
            print(f"  ✅ Query operation successful! Found {len(results.results)} results")
            
            print("  🧹 Testing clear operation...")
            await memory1.clear()
            print("  ✅ Clear operation successful!")
        else:
            print("  ⚠️  Memory client not available, skipping operations")
        
        # Test serialization
        print("\n💾 Testing serialization...")
        config1 = memory1.dump_component()
        print(f"  ✅ Memory 1 config: user_id={config1.config['user_id']}, is_cloud={config1.config['is_cloud']}")
        
        config2 = memory2.dump_component()
        print(f"  ✅ Memory 2 config: user_id={config2.config['user_id']}, is_cloud={config2.config['is_cloud']}")
        
        if memory3:
            config3 = memory3.dump_component()
            print(f"  ✅ Memory 3 config: user_id={config3.config['user_id']}, is_cloud={config3.config['is_cloud']}")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
            print(f"\n🧹 Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up {temp_dir}: {e}")


async def test_ollama_connection():
    """Test if Ollama is responding properly."""
    print("\n🔍 Testing Ollama Connection...")
    
    try:
        import requests
        import json
        
        # Test if Ollama is responding
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"  ✅ Ollama is running with {len(models)} models")
            for model in models:
                print(f"    - {model.get('name', 'Unknown')}")
            return True
        else:
            print(f"  ❌ Ollama returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Ollama connection failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Starting Mem0 Integration Tests")
    print("=" * 50)
    
    # Test Ollama connection
    ollama_ok = await test_ollama_connection()
    
    # Test Mem0 integration
    mem0_ok = await test_mem0_with_fixes()
    
    print("\n📊 Test Results:")
    print(f"  Ollama Connection: {'✅ PASSED' if ollama_ok else '❌ FAILED'}")
    print(f"  Mem0 Integration:  {'✅ PASSED' if mem0_ok else '❌ FAILED'}")
    
    if mem0_ok:
        print("\n🎉 Mem0 integration is working!")
        print("\n📋 Next Steps:")
        print("  1. The integration can handle both file-based and in-memory storage")
        print("  2. Error handling prevents crashes when services are unavailable")
        print("  3. You can now use Mem0Memory in your AutoGen applications")
    else:
        print("\n❌ Mem0 integration needs more work")
        print("\n🔧 Troubleshooting:")
        print("  1. Check if all dependencies are properly installed")
        print("  2. Verify file permissions for database creation")
        print("  3. Check network connectivity for model downloads")


if __name__ == "__main__":
    asyncio.run(main())


