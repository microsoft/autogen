@AutoGen.SemanticKernel.SemanticKernelAgent only supports the original `ChatMessageContent` type via `IMessage<ChatMessageContent>`. To support more AutoGen built-in message types like @AutoGen.Core.TextMessage, @AutoGen.Core.ImageMessage, @AutoGen.Core.MultiModalMessage, you can register the agent with @AutoGen.SemanticKernel.SemanticKernelChatMessageContentConnector. The @AutoGen.SemanticKernel.SemanticKernelChatMessageContentConnector will convert the message from AutoGen built-in message types to `ChatMessageContent` and vice versa.
> [!NOTE]
> At the current stage, @AutoGen.SemanticKernel.SemanticKernelChatMessageContentConnector only supports conversation for the followng built-in @AutoGen.Core.IMessage
> - @AutoGen.Core.TextMessage
> - @AutoGen.Core.ImageMessage
> - @AutoGen.Core.MultiModalMessage
>
> Function call message type like @AutoGen.Core.ToolCallMessage and @AutoGen.Core.ToolCallResultMessage are not supported yet.

[!code-csharp[](../../../samples/AgentChat/Autogen.Basic.Sample/CodeSnippet/SemanticKernelCodeSnippet.cs?name=register_semantic_kernel_chat_message_content_connector)]