## Consume LLM server from LM Studio
You can use @AutoGen.LMStudio.LMStudioAgent from `AutoGen.LMStudio` package to consume openai-like API from LMStudio local server.

### What's LM Studio
[LM Studio](https://lmstudio.ai/) is an app that allows you to deploy and inference hundreds of thousands of open-source language model on your local machine. It provides an in-app chat ui plus an openai-like API to interact with the language model programmatically.

### Installation
- Install LM studio if you haven't done so. You can find the installation guide [here](https://lmstudio.ai/)
- Add `AutoGen.LMStudio` to your project.
```xml
<ItemGroup>
    <PackageReference Include="AutoGen.LMStudio" Version="AUTOGEN_LMSTUDIO_VERSION" />
</ItemGroup>
```

### Usage
The following code shows how to use `LMStudioAgent` to write a piece of C# code to calculate 100th of fibonacci. Before running the code, make sure you have local server from LM Studio running on `localhost:1234`.

[!code-csharp[](../../samples/AutoGen.BasicSamples/Example08_LMStudio.cs?name=lmstudio_using_statements)]
[!code-csharp[](../../samples/AutoGen.BasicSamples/Example08_LMStudio.cs?name=lmstudio_example_1)]
