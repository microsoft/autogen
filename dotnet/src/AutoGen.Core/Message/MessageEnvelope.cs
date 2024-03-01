// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageEnvelope.cs

using System.Collections.Generic;

namespace AutoGen.Core;

public class MessageEnvelope<T> : IMessage<T>, IStreamingMessage<T>
{
    public MessageEnvelope(T content, string? from = null, IDictionary<string, object>? metadata = null)
    {
        this.Content = content;
        this.From = from;
        this.Metadata = metadata ?? new Dictionary<string, object>();
    }

    public T Content { get; }

    public string? From { get; set; }

    public IDictionary<string, object> Metadata { get; set; }
}
