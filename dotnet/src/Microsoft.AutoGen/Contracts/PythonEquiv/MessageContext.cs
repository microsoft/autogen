// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageContext.cs

namespace Microsoft.AutoGen.Contracts.Python;

public class MessageContext(string messageId, CancellationToken cancellationToken)
{
    public string MessageId { get; set; } = messageId;
    public CancellationToken CancellationToken { get; set; } = cancellationToken;

    public AgentId? Sender { get; set; }
    public TopicId? Topic { get; set; }

    public bool IsRpc { get; set; }
}

