# AutoGen for .NET

Thre are two sets of packages here:
AutoGen.\* the older packages derived from AutoGen 0.2 for .NET - these will gradually be deprecated and ported into the new packages
Microsoft.AutoGen.* the new packages for .NET that use the event-driven model - These APIs are not yet stable and are subject to change.

To get started with the new packages, please see the [samples](./samples/) and in particular the [Hello](./samples/Hello) sample.

You can install both new and old packages from the following feeds:

[![dotnet-ci](https://github.com/microsoft/autogen/actions/workflows/dotnet-build.yml/badge.svg)](https://github.com/microsoft/autogen/actions/workflows/dotnet-build.yml)
[![NuGet version](https://badge.fury.io/nu/AutoGen.Core.svg)](https://badge.fury.io/nu/AutoGen.Core)

> [!NOTE]
> Nightly build is available at:
>
> - [![Static Badge](https://img.shields.io/badge/azure_devops-grey?style=flat)](https://dev.azure.com/AGPublish/AGPublic/_artifacts/feed/AutoGen-Nightly) : <https://pkgs.dev.azure.com/AGPublish/AGPublic/_packaging/AutoGen-Nightly/nuget/v3/index.json>

Firstly, following the [installation guide](./website/articles/Installation.md) to install AutoGen packages.

Then you can start with the following code snippet to create a conversable agent and chat with it.

```csharp
using AutoGen;
using AutoGen.OpenAI;

var openAIKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new Exception("Please set OPENAI_API_KEY environment variable.");
var gpt35Config = new OpenAIConfig(openAIKey, "gpt-3.5-turbo");

var assistantAgent = new AssistantAgent(
    name: "assistant",
    systemMessage: "You are an assistant that help user to do some tasks.",
    llmConfig: new ConversableAgentConfig
    {
        Temperature = 0,
        ConfigList = [gpt35Config],
    })
    .RegisterPrintMessage(); // register a hook to print message nicely to console

// set human input mode to ALWAYS so that user always provide input
var userProxyAgent = new UserProxyAgent(
    name: "user",
    humanInputMode: ConversableAgent.HumanInputMode.ALWAYS)
    .RegisterPrintMessage();

// start the conversation
await userProxyAgent.InitiateChatAsync(
    receiver: assistantAgent,
    message: "Hey assistant, please do me a favor.",
    maxRound: 10);
```

## Samples

You can find more examples under the [sample project](https://github.com/microsoft/autogen/tree/dotnet/samples/AutoGen.BasicSamples).

## Functionality

- ConversableAgent
  - [x] function call
  - [x] code execution (dotnet only, powered by [`dotnet-interactive`](https://github.com/dotnet/interactive))

- Agent communication
  - [x] Two-agent chat
  - [x] Group chat

- [ ] Enhanced LLM Inferences

- Exclusive for dotnet
  - [x] Source generator for type-safe function definition generation
