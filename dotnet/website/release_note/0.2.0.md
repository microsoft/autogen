# Release Notes for AutoGen.Net v0.2.0 🚀

## New Features 🌟
- **OpenAI Structural Format Output**: Added support for structural output format in the OpenAI integration. You can check out the example [here](https://github.com/microsoft/autogen/blob/main/dotnet/samples/AutoGen.OpenAI.Sample/Structural_Output.cs) ([#3482](https://github.com/microsoft/autogen/issues/3482)).
- **Structural Output Configuration**: Introduced a property for overriding the structural output schema when generating replies with `GenerateReplyOption` ([#3436](https://github.com/microsoft/autogen/issues/3436)).

## Bug Fixes 🐛
- **Fixed Error Code 500**: Resolved an issue where an error occurred when the message history contained multiple different tool calls with the `name` field ([#3437](https://github.com/microsoft/autogen/issues/3437)).

## Improvements 🔧
- **Leverage OpenAI V2.0 in AutoGen.OpenAI  package**: The `AutoGen.OpenAI` package now uses OpenAI v2.0, providing improved functionality and performance. In the meantime, the original `AutoGen.OpenAI` is still available and can be accessed by `AutoGen.OpenAI.V1`. This allows users who prefer to continue to use `Azure.AI.OpenAI v1` package in their project. ([#3193](https://github.com/microsoft/autogen/issues/3193)).
- **Deprecation of GPTAgent**: `GPTAgent` has been deprecated in favor of `OpenAIChatAgent` and `OpenAIMessageConnector` ([#3404](https://github.com/microsoft/autogen/issues/3404)).

## Documentation 📚
- **Tool Call Instructions**: Added detailed documentation on using tool calls with `ollama` and `OpenAIChatAgent` ([#3248](https://github.com/microsoft/autogen/issues/3248)).

### Migration Guides 🔄

#### For the Deprecation of `GPTAgent` ([#3404](https://github.com/microsoft/autogen/issues/3404)):
**Before:**
```csharp
var agent = new GPTAgent(...);
```
**After:**
```csharp
var agent = new OpenAIChatAgent(...)
    .RegisterMessageConnector();
```

#### For Using Azure.AI.OpenAI v2.0 ([#3193](https://github.com/microsoft/autogen/issues/3193)):
**Previous way of creating `OpenAIChatAgent`:**
```csharp
var openAIClient = new OpenAIClient(apiKey);
var openAIClientAgent = new OpenAIChatAgent(
            openAIClient: openAIClient,
            model: "gpt-4o-mini",
            // Other parameters...
            );
```

**New way of creating `OpenAIChatAgent`:**
```csharp
var openAIClient = new OpenAIClient(apiKey);
var openAIClientAgent = new OpenAIChatAgent(
            chatClient: openAIClient.GetChatClient("gpt-4o-mini"),
            // Other parameters...
            );
```