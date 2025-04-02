## AutoGen.SemanticKernel Overview

AutoGen.SemanticKernel is a package that provides seamless integration with Semantic Kernel. It provides the following agents:
- @AutoGen.SemanticKernel.SemanticKernelAgent: A slim wrapper agent over `Kernel` that only support original `ChatMessageContent` type via `IMessage<ChatMessageContent>`. To support more AutoGen built-in message type, register the agent with @AutoGen.SemanticKernel.SemanticKernelChatMessageContentConnector.
- @AutoGen.SemanticKernel.SemanticKernelChatCompletionAgent: A slim wrapper agent over `Microsoft.SemanticKernel.Agents.ChatCompletionAgent`.

AutoGen.SemanticKernel also provides the following middleware:
- @AutoGen.SemanticKernel.SemanticKernelChatMessageContentConnector: A connector that convert the message from AutoGen built-in message types to `ChatMessageContent` and vice versa. At the current stage, it only supports conversation between @AutoGen.Core.TextMessage, @AutoGen.Core.ImageMessage and @AutoGen.Core.MultiModalMessage. Function call message type like @AutoGen.Core.ToolCallMessage and @AutoGen.Core.ToolCallResultMessage are not supported yet.
- @AutoGen.SemanticKernel.KernelPluginMiddleware: A middleware that allows you to use semantic kernel plugins in other AutoGen agents like @AutoGen.OpenAI.OpenAIChatAgent.

### Get start with AutoGen.SemanticKernel

To get start with AutoGen.SemanticKernel, firstly, follow the [installation guide](../Installation.md) to make sure you add the AutoGen feed correctly. Then add `AutoGen.SemanticKernel` package to your project file.

```xml
<ItemGroup>
    <PackageReference Include="AutoGen.SemanticKernel" Version="AUTOGEN_VERSION" />
</ItemGroup>
```