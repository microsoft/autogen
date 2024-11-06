// Copyright (c) Microsoft Corporation. All rights reserved.
// InferenceAgent.cs

using Google.Protobuf;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.AI;
namespace Microsoft.AutoGen.Agents;
public abstract class InferenceAgent<T> : AgentBase where T : IMessage, new()
{
    protected IChatClient ChatClient { get; }
    public InferenceAgent(
        IAgentRuntime context,
        EventTypes typeRegistry, IChatClient client
        ) : base(context, typeRegistry)
    {
        ChatClient = client;
    }

    private Task<ChatCompletion> CompleteAsync(
        IList<ChatMessage> chatMessages,
        ChatOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return ChatClient.CompleteAsync(chatMessages, options, cancellationToken);
    }

    private IAsyncEnumerable<StreamingChatCompletionUpdate> CompleteStreamingAsync(
        IList<ChatMessage> chatMessages,
        ChatOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return ChatClient.CompleteStreamingAsync(chatMessages, options, cancellationToken);
    }

}
