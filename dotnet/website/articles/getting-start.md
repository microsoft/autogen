## AutoGen for .NET

[![dotnet-ci](https://github.com/microsoft/autogen/actions/workflows/dotnet-build.yml/badge.svg)](https://github.com/microsoft/autogen/actions/workflows/dotnet-build.yml)

### Get start with AutoGen for dotnet
Firstly, following the [installation guide](Installation.md) to install AutoGen packages.

Then you can start with the following code snippet to create a conversable agent and chat with it.

[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/GetStartCodeSnippet.cs?name=snippet_GetStartCodeSnippet)]
[!code-csharp[](../../sample/AutoGen.BasicSamples/CodeSnippet/GetStartCodeSnippet.cs?name=code_snippet_1)]

### Functionality
- ConversableAgent
    - [x] function call
    - [x] code execution (dotnet only, powered by [`dotnet-interactive`](https://github.com/dotnet/interactive))

- Agent communication
    - [x] Two-agent chat
    - [x] Group chat

- [ ] Enhanced LLM Inferences

- Exclusive for dotnet
    - [x] Source generator for type-safe function definition generation

### Update log
[!INCLUDE [Update log](../../nuget/NUGET.md)]