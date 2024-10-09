This example shows how to use @AutoGen.Ollama.OllamaAgent to connect to Ollama server and chat with LLaVA model.

To run this example, you need to have an Ollama server running aside and have `llama3:latest` model installed. For how to setup an Ollama server, please refer to [Ollama](https://ollama.com/).

> [!NOTE]
> You can find the complete sample code [here](https://github.com/microsoft/autogen/blob/main/dotnet/samples/AutoGen.Ollama.Sample/Chat_With_LLaMA.cs)

### Step 1: Install AutoGen.Ollama

First, install the AutoGen.Ollama package using the following command:

```bash
dotnet add package AutoGen.Ollama
```

For how to install from nightly build, please refer to [Installation](../Installation.md).

### Step 2: Add using statement

[!code-csharp[](../../../samples/AutoGen.Ollama.Sample/Chat_With_LLaMA.cs?name=Using)]

### Step 3: Create and chat @AutoGen.Ollama.OllamaAgent

In this step, we create an @AutoGen.Ollama.OllamaAgent and connect it to the Ollama server.

[!code-csharp[](../../../samples/AutoGen.Ollama.Sample/Chat_With_LLaMA.cs?name=Create_Ollama_Agent)]

