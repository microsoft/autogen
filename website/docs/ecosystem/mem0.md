# Mem0: Long-Term Memory and Personalization for Agents

<img src="https://github.com/mem0ai/mem0/blob/main/docs/images/mem0-bg.png?raw=true" alt="Mem0 logo" style="width: 40%;" />

[Mem0 Platform](https://www.mem0.ai/) provides a smart, self-improving memory layer for Large Language Models (LLMs), enabling developers to create personalized AI experiences that evolve with each user interaction.

At a high level, Mem0 Platform offers comprehensive memory management, self-improving memory capabilities, cross-platform consistency, and centralized memory control for AI applications. For more info, check out the [Mem0 Platform Documentation](https://docs.mem0.ai).

|                                          |                                                                   |
| ---------------------------------------- | ----------------------------------------------------------------- |
| 🧠 **Comprehensive Memory Management**   | Manage long-term, short-term, semantic, and episodic memories     |
| 🔄 **Self-Improving Memory**             | Adaptive system that learns from user interactions                |
| 🌐 **Cross-Platform Consistency**        | Unified user experience across various AI platforms               |
| 🎛️ **Centralized Memory Control**        | Effortless storage, updating, and deletion of memories            |
| 🚀 **Simplified Development**            | API-first approach for streamlined integration                    |

<details open>
  <summary><b><u>Activity Dashboard</u></b></summary>
  <a href="https://app.mem0.ai/">
   <img src="https://github.com/mem0ai/mem0/blob/main/docs/images/platform/activity.png?raw=true" style="width: 70%;" alt="Activity Dashboard"/>
  </a>
</details>

## Installation

Mem0 Platform works seamlessly with various AI applications.

1. **Sign Up:**
Create an account at [Mem0 Platform](https://app.mem0.ai/)

2. **Generate API Key:**
Create an API key in your Mem0 dashboard

3. **Install Mem0 SDK:**
```bash
pip install mem0ai
```

4. **Configure Your Environment:**
Add your API key to your environment variables

```
MEM0_API_KEY=<YOUR_MEM0_API_KEY>
```

5. **Initialize Mem0:**

```python
from mem0ai import MemoryClient
memory = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
```

After initializing Mem0, you can start using its memory management features in your AI application.

## Features

- **Long-term Memory**: Store and retrieve information persistently across sessions
- **Short-term Memory**: Manage temporary information within a single interaction
- **Semantic Memory**: Organize and retrieve conceptual knowledge
- **Episodic Memory**: Store and recall specific events or experiences
- **Self-Improving System**: Continuously refine understanding based on user interactions

## Common Use Cases

- Personalized Learning Assistants
- Customer Support AI Agents
- Healthcare Assistants
- Virtual Companions

## Mem0 Platform Examples

### AutoGen with Mem0 Example

This example demonstrates how to use Mem0 with AutoGen to create a conversational AI system with memory capabilities.

```python
import os
from autogen import ConversableAgent
from mem0 import MemoryClient

# Set up environment variables
os.environ["OPENAI_API_KEY"] = "your_openai_api_key"
os.environ["MEM0_API_KEY"] = "your_mem0_api_key"

# Initialize Agent and Memory
agent = ConversableAgent(
    "chatbot",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ.get("OPENAI_API_KEY")}]},
    code_execution_config=False,
    function_map=None,
    human_input_mode="NEVER",
)

memory = MemoryClient(api_key=os.environ.get("MEM0_API_KEY"))

# Insert a conversation into memory
conversation = [
   {
        "role": "assistant",
        "content": "Hi, I'm Best Buy's chatbot!\n\nThanks for being a My Best Buy TotalTM member.\n\nWhat can I help you with?"
    },
    {
        "role": "user",
        "content": "Seeing horizontal lines on our tv. TV model: Sony - 77\" Class BRAVIA XR A80K OLED 4K UHD Smart Google TV"
    },
]

memory.add(messages=conversation, user_id="customer_service_bot")

# Agent Inference
data = "Which TV am I using?"

relevant_memories = memory.search(data, user_id="customer_service_bot")
flatten_relevant_memories = "\n".join([m["memory"] for m in relevant_memories])

prompt = f"""Answer the user question considering the memories.
Memories:
{flatten_relevant_memories}
\n\n
Question: {data}
"""

reply = agent.generate_reply(messages=[{"content": prompt, "role": "user"}])
print("Reply :", reply)

# Multi Agent Conversation
manager = ConversableAgent(
    "manager",
    system_message="You are a manager who helps in resolving customer issues.",
    llm_config={"config_list": [{"model": "gpt-4", "temperature": 0, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER"
)

customer_bot = ConversableAgent(
    "customer_bot",
    system_message="You are a customer service bot who gathers information on issues customers are facing.",
    llm_config={"config_list": [{"model": "gpt-4", "temperature": 0, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER"
)

data = "What appointment is booked?"

relevant_memories = memory.search(data, user_id="customer_service_bot")
flatten_relevant_memories = "\n".join([m["memory"] for m in relevant_memories])

prompt = f"""
Context:
{flatten_relevant_memories}
\n\n
Question: {data}
"""

result = manager.send(prompt, customer_bot, request_reply=True)
```

Access the complete code from this notebook: [Mem0 with AutoGen](https://colab.research.google.com/drive/1NZEwC9w6V2S6hYmK7l2SQ9jhQrG1uKk8?usp=sharing)

This example showcases:
1. Setting up AutoGen agents and Mem0 memory
2. Adding a conversation to Mem0 memory
3. Using Mem0 to retrieve relevant memories for agent inference
4. Implementing a multi-agent conversation with memory-augmented context

For more Mem0 examples, visit our [documentation](https://docs.mem0.ai/examples).
