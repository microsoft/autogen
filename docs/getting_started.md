# Getting Started with AutoGen

This guide will help you get started with AutoGen by providing detailed installation instructions, code examples, and instructions for setting up API keys.

## Installation Instructions

### Python

1. **Install Python**: Ensure you have Python 3.8 or later installed. You can download it from [python.org](https://www.python.org/downloads/).

2. **Create a Virtual Environment**: It's recommended to create a virtual environment to manage dependencies.
   ```sh
   python -m venv autogen-env
   source autogen-env/bin/activate  # On Windows use `autogen-env\Scripts\activate`
   ```

3. **Install AutoGen Packages**: Use `pip` to install the necessary AutoGen packages.
   ```sh
   pip install autogen-core autogen-agentchat autogen-ext
   ```

### C#

1. **Install .NET SDK**: Ensure you have .NET 6.0 SDK or later installed. You can download it from [dotnet.microsoft.com](https://dotnet.microsoft.com/download).

2. **Create a New Project**: Create a new console application.
   ```sh
   dotnet new console -n AutoGenApp
   cd AutoGenApp
   ```

3. **Add AutoGen Packages**: Use `dotnet add package` to install the necessary AutoGen packages.
   ```sh
   dotnet add package AutoGen.Core
   dotnet add package AutoGen.AgentChat
   dotnet add package AutoGen.Ext
   ```

## Code Examples

### Python

Here is a simple example of creating an agent and sending a message in Python:

```python
from autogen_core import Agent, Message

class MyAgent(Agent):
    def handle_message(self, message: Message):
        print(f"Received message: {message.content}")

agent = MyAgent()
agent.send_message(Message(content="Hello, AutoGen!"))
```

### C#

Here is a simple example of creating an agent and sending a message in C#:

```csharp
using AutoGen.Core;
using AutoGen.AgentChat;

public class MyAgent : Agent
{
    public override void HandleMessage(Message message)
    {
        Console.WriteLine($"Received message: {message.Content}");
    }
}

var agent = new MyAgent();
agent.SendMessage(new Message { Content = "Hello, AutoGen!" });
```

## Setting Up API Keys

To use certain features of AutoGen, you may need to set up API keys for external services.

### OpenAI

1. **Get an API Key**: Sign up for an API key at [OpenAI](https://beta.openai.com/signup/).

2. **Set the API Key**: Set the API key as an environment variable.
   ```sh
   export OPENAI_API_KEY='your-api-key'  # On Windows use `set OPENAI_API_KEY=your-api-key`
   ```

### Azure

1. **Get an API Key**: Sign up for an API key at [Azure](https://azure.microsoft.com/en-us/free/).

2. **Set the API Key**: Set the API key as an environment variable.
   ```sh
   export AZURE_API_KEY='your-api-key'  # On Windows use `set AZURE_API_KEY=your-api-key`
   ```

For more detailed information, please refer to the [official documentation](https://microsoft.github.io/autogen/).
