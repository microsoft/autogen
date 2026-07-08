// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatAgentBase.cs

using System.Runtime.CompilerServices;
using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.Agents;

/// <summary>
/// Base class for a chat agent.
/// </summary>
public abstract class ChatAgentBase : IChatAgent
{
    public ChatAgentBase(string name, string description)
    {
        Name = new AgentName(name);
        Description = description;
    }

    /// <inheritdoc cref="IChatAgent.Name"/>
    public AgentName Name { get; }

    /// <inheritdoc cref="IChatAgent.Description"/>
    public string Description { get; }

    /// <inheritdoc cref="IHandleStream{TIn, TOut}.StreamAsync(TIn, CancellationToken)"/>
    public virtual async IAsyncEnumerable<ChatStreamFrame> StreamAsync(IEnumerable<ChatMessage> item, [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        Response response = await (this).HandleAsync(item, cancellationToken);
        if (response.InnerMessages != null)
        {
            foreach (var message in response.InnerMessages)
            {
                // It would be really nice to have type unions in .NET; need to think about how to make this interface nicer.
                yield return new ChatStreamFrame { Type = ChatStreamFrame.FrameType.InternalMessage, InternalMessage = message };
            }
        }

        yield return new ChatStreamFrame { Type = ChatStreamFrame.FrameType.Response, Response = response };
    }

    /// <inheritdoc cref="IChatAgent.ProducedMessageTypes"/>
    public abstract IEnumerable<Type> ProducedMessageTypes { get; }

    /// <inheritdoc cref="IHandleChat{TIn, TOut}.HandleAsync(TIn, CancellationToken)"/>
    public abstract ValueTask<Response> HandleAsync(IEnumerable<ChatMessage> item, CancellationToken cancellationToken);

    /// <inheritdoc cref="IChatAgent.ResetAsync(CancellationToken)"/>
    public abstract ValueTask ResetAsync(CancellationToken cancellationToken);
}
