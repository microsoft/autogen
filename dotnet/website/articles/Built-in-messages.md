## An overview of built-in @AutoGen.Core.IMessage types

Start from 0.0.9, AutoGen introduces the @AutoGen.Core.IMessage and @AutoGen.Core.IMessage`1 types to provide a unified message interface for different agents. The @AutoGen.Core.IMessage is a non-generic interface that represents a message. The @AutoGen.Core.IMessage`1 is a generic interface that represents a message with a specific `T` where `T` can be any type.

Besides, AutoGen also provides a set of built-in message types that implement the @AutoGen.Core.IMessage and @AutoGen.Core.IMessage`1 interfaces. These built-in message types are designed to cover different types of messages as much as possilbe. The built-in message types include:

> [!NOTE]
> The minimal requirement for an agent to be used as admin in @AutoGen.Core.GroupChat is to support @AutoGen.Core.TextMessage.

> [!NOTE]
> @AutoGen.Core.Message will be deprecated in 0.0.14. Please replace it with a more specific message type like @AutoGen.Core.TextMessage, @AutoGen.Core.ImageMessage, etc.

- @AutoGen.Core.TextMessage: A message that contains a piece of text.
- @AutoGen.Core.ImageMessage: A message that contains an image.
- @AutoGen.Core.MultiModalMessage: A message that contains multiple modalities like text, image, etc.
- @AutoGen.Core.ToolCallMessage: A message that represents a function call request.
- @AutoGen.Core.ToolCallResultMessage: A message that represents a function call result.
- @AutoGen.Core.ToolCallAggregateMessage: A message that contains both @AutoGen.Core.ToolCallMessage and @AutoGen.Core.ToolCallResultMessage. This type of message is used by @AutoGen.Core.FunctionCallMiddleware to aggregate both @AutoGen.Core.ToolCallMessage and @AutoGen.Core.ToolCallResultMessage into a single message.
- @AutoGen.Core.MessageEnvelope`1: A message that represents an envelope that contains a message of any type.
- @AutoGen.Core.Message: The original message type before 0.0.9. This message type is reserved for backward compatibility. It is recommended to replace it with a more specific message type like @AutoGen.Core.TextMessage, @AutoGen.Core.ImageMessage, etc.

### Streaming message support
AutoGen also introduces @AutoGen.Core.IStreamingMessage and @AutoGen.Core.IStreamingMessage`1 which are used in streaming call api. The following built-in message types implement the @AutoGen.Core.IStreamingMessage and @AutoGen.Core.IStreamingMessage`1 interfaces:

> [!NOTE]
> All @AutoGen.Core.IMessage is also a @AutoGen.Core.IStreamingMessage. That means you can return an @AutoGen.Core.IMessage from a streaming call method. It's also recommended to return the final updated result instead of the last update as the last message in the streaming call method to indicate the end of the stream, which saves caller's effort of assembling the final result from multiple updates. 
- @AutoGen.Core.TextMessageUpdate: A message that contains a piece of text update.
- @AutoGen.Core.ToolCallMessageUpdate: A message that contains a function call request update.

#### Usage

The below code snippet shows how to print a streaming update to console and update the final result on the caller side.
[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/BuildInMessageCodeSnippet.cs?name=StreamingCallCodeSnippet)]

If the agent returns a final result instead of the last update as the last message in the streaming call method, the caller can directly use the final result without assembling the final result from multiple updates.

[!code-csharp[](../../samples/AutoGen.BasicSamples/CodeSnippet/BuildInMessageCodeSnippet.cs?name=StreamingCallWithFinalMessage)]