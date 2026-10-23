## Consume LLM server from LM Studio
You can use @AutoGen.OpenAI.OpenAIChatAgent from `AutoGen.OpenAI` package to consume an OpenAI-compatible API from a local LM Studio server.

### What's LM Studio
[LM Studio](https://lmstudio.ai/) is an app that allows you to deploy and inference hundreds of thousands of open-source language model on your local machine. It provides an in-app chat ui plus an openai-like API to interact with the language model programmatically.

### Installation
- Install LM studio if you haven't done so. You can find the installation guide [here](https://lmstudio.ai/)
- Add `AutoGen.OpenAI` to your project.
```xml
<ItemGroup>
    <PackageReference Include="AutoGen.OpenAI" Version="AUTOGEN_VERSION" />
</ItemGroup>
```

### Usage
The following code shows how to use `OpenAIChatAgent` to write a piece of C# code to calculate 100th of fibonacci. Before running the code, make sure you have local server from LM Studio running on `localhost:1234`.

[!code-csharp[](../../samples/AgentChat/AutoGen.Basic.Sample/Example08_LMStudio.cs?name=lmstudio_using_statements)]
[!code-csharp[](../../samples/AgentChat/AutoGen.Basic.Sample/Example08_LMStudio.cs?name=lmstudio_example_1)]
