// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageContext.cs

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Represents the context of a message being sent within the agent runtime.
/// This includes metadata such as the sender, topic, RPC status, and cancellation handling.
/// </summary>
public class MessageContext(string messageId, CancellationToken cancellationToken)
{
    /// <summary>
    /// Gets or sets the unique identifier for this message.
    /// </summary>
    public string MessageId { get; set; } = messageId;

    /// <summary>
    /// Gets or sets the cancellation token associated with this message.
    /// This can be used to cancel the operation if necessary.
    /// </summary>
    public CancellationToken CancellationToken { get; set; } = cancellationToken;

    /// <summary>
    /// Gets or sets the sender of the message.
    /// If <c>null</c>, the sender is unspecified.
    /// </summary>
    public AgentId? Sender { get; set; }

    /// <summary>
    /// Gets or sets the topic associated with the message.
    /// If <c>null</c>, the message is not tied to a specific topic.
    /// </summary>
    public TopicId? Topic { get; set; }

    /// <summary>
    /// Gets or sets a value indicating whether this message is part of an RPC (Remote Procedure Call).
    /// </summary>
    public bool IsRpc { get; set; }
}

