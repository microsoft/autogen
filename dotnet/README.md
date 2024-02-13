### AutoGen for .NET

[![dotnet-ci](https://github.com/microsoft/autogen/actions/workflows/dotnet-build.yml/badge.svg)](https://github.com/microsoft/autogen/actions/workflows/dotnet-build.yml)

#### Get start with AutoGen for dotnet
Firstly, select one of the following package feed to consume AutoGen packages:
- ![Static Badge](https://img.shields.io/badge/public-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/github-grey?style=flat): https://nuget.pkg.github.com/microsoft/index.json
- ![Static Badge](https://img.shields.io/badge/public-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/myget-grey?style=flat): https://www.myget.org/F/agentchat/api/v3/index.json
- ![Static Badge](https://img.shields.io/badge/internal-blue?style=flat) ![Static Badge](https://img.shields.io/badge/nightly-yellow?style=flat) ![Static Badge](https://img.shields.io/badge/azure_devops-grey?style=flat) : https://devdiv.pkgs.visualstudio.com/DevDiv/_packaging/AutoGen/nuget/v3/index.json


Then, add the following to your project file:
```xml
<ItemGroup>
    <PackageReference Include="AutoGen" />

    <!-- Optional: This package carries a source generator that adds support for type-safe function definition generation. -->
    <!-- For more information, please check out AutoGen.SourceGenerator README -->
    <PackageReference Include="AutoGen.SourceGenerator" />

    <!-- Optional: This packages carries dotnet interactive support to execute dotnet code snippet -->
    <PackageReference Include="AutoGen.DotnetInteractive" />
</ItemGroup>
```

Then, start using AutoGen in your code:

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
    .RegisterPrintFormatMessageHook(); // register a hook to print message nicely to console

// set human input mode to ALWAYS so that user always provide input
var userProxyAgent = new UserProxyAgent(
    name: "user",
    humanInputMode: ConversableAgent.HumanInputMode.ALWAYS)
    .RegisterPrintFormatMessageHook();

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
##### 2024-01-04
- update Azure.OpenAI.AI to 1.0.0-beta.12
- update Semantic kernel to 1.0.1
- add support and example for GPT-4-Vision-Preview
