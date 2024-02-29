## AutoGen.GenericAPI

This package provides support for consuming openai-like API for other providers like Mistral, Groq, OpenRouter.

## Installation
To use `AutoGen.GenericApi`, add the following package to your `.csproj` file:

```xml
<ItemGroup>
    <PackageReference Include="AutoGen.GenericApi" Version="AUTOGEN_VERSION" />
</ItemGroup>
```

## Usage
```csharp
using AutoGen.GenericAPI;
var mistralAIKey = Environment.GetEnvironmentVariable("MISTRAL_API_KEY") ?? throw new Exception("Please set MISTRAL_API_KEY environment variable.");
var mistralEndpoint = "api.mistral.ai";
var genericConfig = new GenericAgentConfig(mistralAIKey, mistralEndpoint);
var agent = new GenericAgent(
    name: "assistent",
    modelName: "mistral-large-latest",
    systemMessage: "You are an agent that help user to do some tasks.",
    config: genericConfig)
    .RegisterPrintFormatMessageHook(); // register a hook to print message nicely to console

await agent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
```

## Update history
### Update  (2024-02-28)
- Add `GenericAgent` to support consuming openai-like API from different vendors like Mistral, Groq or OpenRouter.
