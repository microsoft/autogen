##### Update on 0.0.15 (2024-06-13) Milestone: [AutoGen.Net 0.0.15](https://github.com/microsoft/autogen/milestone/3)

###### Highlights
- [Issue 2851](https://github.com/microsoft/autogen/issues/2851) `AutoGen.Gemini` package for Gemini support. Examples can be found [here](https://github.com/microsoft/autogen/tree/main/dotnet/sample/AutoGen.Gemini.Sample)

##### Update on 0.0.14 (2024-05-28)
###### New features
- [Issue 2319](https://github.com/microsoft/autogen/issues/2319) Add `AutoGen.Ollama` package for Ollama support. Special thanks to @iddelacruz for the effort.
- [Issue 2608](https://github.com/microsoft/autogen/issues/2608) Add `AutoGen.Anthropic` package for Anthropic support. Special thanks to @DavidLuong98 for the effort.
- [Issue 2647](https://github.com/microsoft/autogen/issues/2647) Add `ToolCallAggregateMessage` for function call middleware.

###### API Breaking Changes
- [Issue 2648](https://github.com/microsoft/autogen/issues/2648) Deprecate `Message` type.
- [Issue 2649](https://github.com/microsoft/autogen/issues/2649) Deprecate `Workflow` type.
###### Bug Fixes
- [Issue 2735](https://github.com/microsoft/autogen/issues/2735) Fix tool call issue in AutoGen.Mistral package.
- [Issue 2722](https://github.com/microsoft/autogen/issues/2722) Fix parallel funciton call in function call middleware.
- [Issue 2633](https://github.com/microsoft/autogen/issues/2633) Set up `name` field in `OpenAIChatMessageConnector`
- [Issue 2660](https://github.com/microsoft/autogen/issues/2660) Fix dotnet interactive restoring issue when system language is Chinese
- [Issue 2687](https://github.com/microsoft/autogen/issues/2687) Add `global::` prefix to generated code to avoid conflict with user-defined types. 
##### Update on 0.0.13 (2024-05-09)
###### New features
- [Issue 2593](https://github.com/microsoft/autogen/issues/2593) Consume SK plugins in Agent.
- [Issue 1893](https://github.com/microsoft/autogen/issues/1893) Support inline-data in ImageMessage
- [Issue 2481](https://github.com/microsoft/autogen/issues/2481) Introduce `ChatCompletionAgent` to `AutoGen.SemanticKernel`
###### API Breaking Changes
- [Issue 2470](https://github.com/microsoft/autogen/issues/2470) Update the return type of `IStreamingAgent.GenerateStreamingReplyAsync` from `Task<IAsyncEnumerable<IStreamingMessage>>` to `IAsyncEnumerable<IStreamingMessage>`
- [Issue 2470](https://github.com/microsoft/autogen/issues/2470) Update the return type of `IStreamingMiddleware.InvokeAsync` from `Task<IAsyncEnumerable<IStreamingMessage>>` to `IAsyncEnumerable<IStreamingMessage>`
- Mark `RegisterReply`, `RegisterPreProcess` and `RegisterPostProcess` as obsolete. You can replace them with `RegisterMiddleware`

###### Bug Fixes
- Fix [Issue 2609](https://github.com/microsoft/autogen/issues/2609) Constructor of conversableAgentConfig does not accept LMStudioConfig as ConfigList

##### Update on 0.0.12 (2024-04-22)
- Add AutoGen.Mistral package to support Mistral.AI models
##### Update on 0.0.11 (2024-04-10)
- Add link to Discord channel in nuget's readme.md
- Document improvements
- In `AutoGen.OpenAI`, update `Azure.AI.OpenAI` to 1.0.0-beta.15 and add support for json mode and deterministic output in `OpenAIChatAgent` [Issue #2346](https://github.com/microsoft/autogen/issues/2346)
- In `AutoGen.SemanticKernel`, update `SemanticKernel` package to 1.7.1
- [API Breaking Change] Rename `PrintMessageMiddlewareExtension.RegisterPrintFormatMessageHook' to `PrintMessageMiddlewareExtension.RegisterPrintMessage`.
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