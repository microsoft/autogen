// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageRegistryState.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;

/// <summary>
/// Holds a dead-letter queue by topic type.
/// </summary>
public class MessageRegistryState
{
    /// <summary>
    /// Dictionary mapping topic types to a list of CloudEvents that failed delivery.
    /// we read from this queue on new sub and registration so that agents can potentially receive messages they missed
    /// </summary>
    public ConcurrentDictionary<string, List<CloudEvent>> DeadLetterQueue { get; set; } = new();
    /// <summary>
    /// A Dictionary of events that have been recently delivered to agents.
    /// We keep them around for a short time to ensure that anyone subscribing to the topic within the next few seconds has a chance to receive them.
    /// </summary>
    public ConcurrentDictionary<string, List<CloudEvent>> EventBuffer { get; set; } = new();
}
