# Mem0 Local Setup Guide

This guide shows you how to launch Mem0 integration locally with AutoGen.

## 🚀 Quick Start

### Option 1: Mock Mode (No External Dependencies)
```bash
cd /workspaces/autogen/python
uv run python ../launch_mem0_local.py --mode mock
```

### Option 2: Cloud Mode (Requires API Key)
```bash
export MEM0_API_KEY=your_api_key_here
cd /workspaces/autogen/python
uv run python ../launch_mem0_local.py --mode cloud
```

### Option 3: Local Mode (Requires Local LLM Server)
```bash
# Install and start Ollama
ollama pull llama2
ollama serve

# In another terminal
cd /workspaces/autogen/python
uv run python ../launch_mem0_local.py --mode local
```

## 📋 What Each Mode Does

### Mock Mode
- ✅ **No external dependencies required**
- ✅ **Perfect for testing and development**
- ✅ **Demonstrates all Mem0 functionality**
- ❌ **Not suitable for production**

### Cloud Mode
- ✅ **Full production functionality**
- ✅ **No local setup required**
- ❌ **Requires Mem0 API key**
- ❌ **Requires internet connection**

### Local Mode
- ✅ **Full production functionality**
- ✅ **No external API calls**
- ✅ **Privacy-friendly**
- ❌ **Requires local LLM server setup**

## 🔧 Installation

### Prerequisites
```bash
# Install dependencies
cd /workspaces/autogen/python
uv sync --extra mem0-local
```

### For Local Mode
```bash
# Install Ollama (recommended)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama2
ollama serve

# Or install LMStudio
# Download from: https://lmstudio.ai/
```

### For Cloud Mode
```bash
# Get API key from: https://app.mem0.ai/dashboard/api-keys
export MEM0_API_KEY=your_key_here
```

## 💻 Usage Examples

### Basic Usage
```python
from autogen_ext.memory.mem0 import Mem0Memory
from autogen_core.memory import MemoryContent

# Create memory instance
memory = Mem0Memory(
    user_id="user123",
    is_cloud=False,  # or True for cloud mode
    config={"path": ":memory:"}  # for local mode
)

# Add memory
await memory.add(MemoryContent(
    content="User likes Python programming",
    mime_type="text/plain"
))

# Query memory
results = await memory.query("What does the user like?")
print(f"Found {len(results.results)} relevant memories")

# Clean up
await memory.clear()
await memory.close()
```

### With AutoGen Agents
```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.memory.mem0 import Mem0Memory

# Create memory
memory = Mem0Memory(
    user_id="user123",
    is_cloud=False,
    config={"path": ":memory:"}
)

# Create agent with memory
agent = AssistantAgent(
    name="assistant",
    model_client=OpenAIChatCompletionClient(model="gpt-4"),
    memory=[memory],
    system_message="You are a helpful assistant with memory."
)

# The agent will automatically use memory for context
result = await agent.run(task="What do you know about the user?")
```

## 🧪 Testing

Run the test suite:
```bash
cd /workspaces/autogen/python
uv run pytest packages/autogen-ext/tests/memory/test_mem0.py -v
```

## 🔍 Troubleshooting

### Common Issues

1. **"Connection refused" errors**
   - Make sure your local LLM server is running
   - Check the correct port (Ollama: 11434, LMStudio: 1234)

2. **"Invalid API key" errors**
   - Check your MEM0_API_KEY environment variable
   - Verify the key is valid at https://app.mem0.ai/dashboard/api-keys

3. **Import errors**
   - Make sure you're in the correct directory
   - Run `uv sync --extra mem0-local` to install dependencies

### Debug Mode
```bash
# Run with verbose output
cd /workspaces/autogen/python
uv run python ../launch_mem0_local.py --mode mock --verbose
```

## 📚 Additional Resources

- [Mem0 Documentation](https://docs.mem0.ai/)
- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [Ollama Documentation](https://ollama.ai/docs)
- [LMStudio Documentation](https://lmstudio.ai/docs)

## 🎉 Success!

If you see "MEM0 LAUNCHED SUCCESSFULLY!" then everything is working correctly!

The Mem0 integration provides:
- ✅ Persistent memory across conversations
- ✅ Natural language memory queries
- ✅ Automatic context updating
- ✅ Metadata support
- ✅ Cloud and local deployment options




