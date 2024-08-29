## AutoGen.OpenAI Overview

AutoGen.OpenAI provides the following agents over openai models:
- @AutoGen.OpenAI.OpenAIChatAgent: A slim wrapper agent over `OpenAIClient`. This agent only support `IMessage<ChatRequestMessage>` message type. To support more message types like @AutoGen.Core.TextMessage, register the agent with @AutoGen.OpenAI.OpenAIChatRequestMessageConnector.
- @AutoGen.OpenAI.GPTAgent: An agent that build on top of @AutoGen.OpenAI.OpenAIChatAgent with more message types support like @AutoGen.Core.TextMessage, @AutoGen.Core.ImageMessage, @AutoGen.Core.MultiModalMessage and function call support. Essentially, it is equivalent to @AutoGen.OpenAI.OpenAIChatAgent with @AutoGen.Core.FunctionCallMiddleware and @AutoGen.OpenAI.OpenAIChatRequestMessageConnector registered.

### Get start with AutoGen.OpenAI

To get start with AutoGen.OpenAI, firstly, follow the [installation guide](Installation.md) to make sure you add the AutoGen feed correctly. Then add `AutoGen.OpenAI` package to your project file.

```xml
<ItemGroup>
    <PackageReference Include="AutoGen.OpenAI" Version="AUTOGEN_VERSION" />
</ItemGroup>
```


