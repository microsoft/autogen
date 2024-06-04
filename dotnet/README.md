### AutoGen for .NET

[![dotnet-ci](https://github.com/microsoft/autogen/actions/workflows/dotnet-build.yml/badge.svg)](https://github.com/microsoft/autogen/actions/workflows/dotnet-build.yml)
[![NuGet version](https://badge.fury.io/nu/AutoGen.Core.svg)](https://badge.fury.io/nu/AutoGen.Core)

> [!NOTE]
> Nightly build is available at:
> - ![Static Badge](https://img.shields.io/badge/public-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/github-grey?style=flat): https://nuget.pkg.github.com/microsoft/index.json
> - ![Static Badge](https://img.shields.io/badge/public-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/myget-grey?style=flat): https://www.myget.org/F/agentchat/api/v3/index.json
> - ![Static Badge](https://img.shields.io/badge/internal-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/azure_devops-grey?style=flat) : https://devdiv.pkgs.visualstudio.com/DevDiv/_packaging/AutoGen/nuget/v3/index.json


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

#### Samples
You can find more examples under the [sample project](https://github.com/microsoft/autogen/tree/dotnet/dotnet/sample/AutoGen.BasicSamples).

#### Functionality
- ConversableAgent
    - [x] function call
    - [x] code execution (dotnet only, powered by [`dotnet-interactive`](https://github.com/dotnet/interactive))

- Agent communication
    - [x] Two-agent chat
    - [x] Group chat

- [ ] Enhanced LLM Inferences

- Exclusive for dotnet
    - [x] Source generator for type-safe function definition generation

#### Update log
##### Update on 0.0.11 (2024-03-26)
- Add link to Discord channel in nuget's readme.md
- Document improvements
##### Update on 0.0.10 (2024-03-12)
- Rename `Workflow` to `Graph`
- Rename `AddInitializeMessage` to `SendIntroduction`
- Rename `SequentialGroupChat` to `RoundRobinGroupChat`
##### Update on 0.0.9 (2024-03-02)
- Refactor over @AutoGen.Message and introducing `TextMessage`, `ImageMessage`, `MultiModalMessage` and so on. PR [#1676](https://github.com/microsoft/autogen/pull/1676)
- Add `AutoGen.SemanticKernel` to support seamless integration with Semantic Kernel
- Move the agent contract abstraction to `AutoGen.Core` package. The `AutoGen.Core` package provides the abstraction for message type, agent and group chat and doesn't contain dependencies over `Azure.AI.OpenAI` or `Semantic Kernel`. This is useful when you want to leverage AutoGen's abstraction only and want to avoid introducing any other dependencies.
- Move `GPTAgent`, `OpenAIChatAgent` and all openai-dependencies to `AutoGen.OpenAI`
##### Update on 0.0.8 (2024-02-28)
- Fix [#1804](https://github.com/microsoft/autogen/pull/1804)
- Streaming support for IAgent [#1656](https://github.com/microsoft/autogen/pull/1656)
- Streaming support for middleware via `MiddlewareStreamingAgent` [#1656](https://github.com/microsoft/autogen/pull/1656)
- Graph chat support with conditional transition workflow [#1761](https://github.com/microsoft/autogen/pull/1761)
- AutoGen.SourceGenerator: Generate `FunctionContract` from `FunctionAttribute` [#1736](https://github.com/microsoft/autogen/pull/1736)
##### Update on 0.0.7 (2024-02-11)
- Add `AutoGen.LMStudio` to support comsume openai-like API from LMStudio local server
##### Update on 0.0.6 (2024-01-23)
- Add `MiddlewareAgent`
- Use `MiddlewareAgent` to implement existing agent hooks (RegisterPreProcess, RegisterPostProcess, RegisterReply)
- Remove `AutoReplyAgent`, `PreProcessAgent`, `PostProcessAgent` because they are replaced by `MiddlewareAgent`
##### Update on 0.0.5
- Simplify `IAgent` interface by removing `ChatLLM` Property
- Add `GenerateReplyOptions` to `IAgent.GenerateReplyAsync` which allows user to specify or override the options when generating reply

##### Update on 0.0.4
- Move out dependency of Semantic Kernel
- Add type `IChatLLM` as connector to LLM

##### Update on 0.0.3
- In AutoGen.SourceGenerator, rename FunctionAttribution to FunctionAttribute
- In AutoGen, refactor over ConversationAgent, UserProxyAgent, and AssistantAgent

##### Update on 0.0.2
- update Azure.OpenAI.AI to 1.0.0-beta.12
- update Semantic kernel to 1.0.1
