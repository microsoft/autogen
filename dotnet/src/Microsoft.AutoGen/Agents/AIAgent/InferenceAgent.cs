// Copyright (c) Microsoft Corporation. All rights reserved.
// InferenceAgent.cs
using Google.Protobuf;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.AI;
using Microsoft.Extensions.Logging;
namespace Microsoft.AutoGen.Agents;
/// <summary>
/// Base class for inference agents using the Microsoft.Extensions.AI library.
/// </summary>
/// <typeparam name="T"></typeparam>
/// <param name="id"></param>
/// <param name="runtime"></param>
/// <param name="name"></param>
/// <param name="logger"></param>
/// <param name="client"></param>
public abstract class InferenceAgent<T>(
    AgentId id,
    IAgentRuntime runtime,
    string name,
    ILogger<InferenceAgent<T>>? logger,
    IChatClient client)
    : BaseAgent(id, runtime, name, logger)
    where T : IMessage, new()
{
    protected IChatClient ChatClient { get; } = client;
    private ILogger<InferenceAgent<T>>? Logger => _logger as ILogger<InferenceAgent<T>>;
    private Task<ChatResponse> CompleteAsync(
        IList<ChatMessage> chatMessages,
        ChatOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return ChatClient.GetResponseAsync(chatMessages, options, cancellationToken);
    }
    private IAsyncEnumerable<ChatResponseUpdate> CompleteStreamingAsync(
        IList<ChatMessage> chatMessages,
        ChatOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return ChatClient.GetStreamingResponseAsync(chatMessages, options, cancellationToken);
    }

}
