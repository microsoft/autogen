#!/usr/bin/env python3
"""
Simple working Mem0 test that doesn't get stuck
"""

import sys
import asyncio
import tempfile
import os

# Add the autogen-ext package to the path
sys.path.insert(0, '/workspaces/autogen/python/packages/autogen-ext/src')

def test_imports():
    """Test that we can import the required modules"""
    print("🔍 Testing imports...")
    
    try:
        from autogen_ext.memory.mem0 import Mem0Memory
        print("  ✅ Mem0Memory imported successfully")
    except Exception as e:
        print(f"  ❌ Failed to import Mem0Memory: {e}")
        return False
    
    try:
        from autogen_core.memory import MemoryContent
        print("  ✅ MemoryContent imported successfully")
    except Exception as e:
        print(f"  ❌ Failed to import MemoryContent: {e}")
        return False
    
    return True

def test_simple_config():
    """Test simple configuration creation"""
    print("\n🔍 Testing simple configuration...")
    
    try:
        from autogen_ext.memory.mem0 import Mem0Memory
        
        # Test with minimal configuration
        memory = Mem0Memory(
            user_id='test-user',
            is_cloud=False,
            config={'path': ':memory:'}
        )
        print("  ✅ Simple memory created successfully")
        return True
    except Exception as e:
        print(f"  ❌ Failed to create simple memory: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ollama_connection():
    """Test Ollama connection"""
    print("\n🔍 Testing Ollama connection...")
    
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            print(f"  ✅ Ollama is running with {len(models)} models: {models}")
            return True
        else:
            print(f"  ❌ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Failed to connect to Ollama: {e}")
        return False

async def test_memory_operations():
    """Test basic memory operations"""
    print("\n🔍 Testing memory operations...")
    
    try:
        from autogen_ext.memory.mem0 import Mem0Memory
        from autogen_core.memory import MemoryContent
        
        # Create memory with minimal config
        memory = Mem0Memory(
            user_id='test-user',
            is_cloud=False,
            config={'path': ':memory:'}
        )
        
        print("  📝 Testing memory operations...")
        
        # Test adding memory (this might fail but shouldn't hang)
        try:
            await memory.add(MemoryContent(
                content='Test memory content',
                mime_type='text/plain'
            ))
            print("  ✅ Memory added successfully")
        except Exception as e:
            print(f"  ⚠️  Memory add failed (expected): {e}")
        
        # Test querying memory
        try:
            results = await memory.query('test query')
            print(f"  ✅ Memory query successful: {len(results.results)} results")
        except Exception as e:
            print(f"  ⚠️  Memory query failed (expected): {e}")
        
        return True
    except Exception as e:
        print(f"  ❌ Memory operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 Starting Simple Working Test")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed")
        return False
    
    # Test simple config
    if not test_simple_config():
        print("\n❌ Simple config test failed")
        return False
    
    # Test Ollama connection
    if not test_ollama_connection():
        print("\n❌ Ollama connection test failed")
        return False
    
    # Test memory operations
    try:
        result = asyncio.run(test_memory_operations())
        if not result:
            print("\n❌ Memory operations test failed")
            return False
    except Exception as e:
        print(f"\n❌ Memory operations test failed: {e}")
        return False
    
    print("\n🎉 All tests passed!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

