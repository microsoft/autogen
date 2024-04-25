## AutoGen.Ollama

This package provides support for consuming openai-like API from Ollama local server.

## Installation
To use `AutoGen.Ollama`, add the following package to your `.csproj` file:

```xml
<ItemGroup>
    <PackageReference Include="AutoGen.Ollama" Version="AUTOGEN_VERSION" />
</ItemGroup>
```

## Usage
```csharp
using AutoGen.Core;
using AutoGen.Ollama;

var config = new OllamaConfig("localhost", 11434);

// You can specify any model Ollama supports.
// See list here: https://ollama.com/library
// Just make sure you "pull" the model using "ollama pull" first.
var assistantAgent = new OllamaAgent("asssistant", config: config, "llama3")
    .RegisterPrintMessage();

// set human input mode to ALWAYS so that user always provide input
var userProxyAgent = new UserProxyAgent(
    name: "user",
    humanInputMode: HumanInputMode.ALWAYS)
    .RegisterPrintMessage();

// start the conversation
await userProxyAgent.InitiateChatAsync(
    receiver: assistantAgent,
    message: "Why is the sky blue?",
    maxRound: 10);

Console.WriteLine("Thanks for using Ollama. https://ollama.com/blog/");
