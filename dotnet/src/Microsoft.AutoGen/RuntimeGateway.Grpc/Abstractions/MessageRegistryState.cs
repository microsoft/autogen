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
    /// </summary>
    public ConcurrentDictionary<string, List<CloudEvent>> DeadLetterQueue { get; set; } = new();
}
