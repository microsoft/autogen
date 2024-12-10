// Copyright (c) Microsoft Corporation. All rights reserved.
// SubscriptionsState.cs
using System.Collections.Concurrent;

namespace Microsoft.AutoGen.Abstractions;
[GenerateSerializer]
[Serializable]
public sealed class SubscriptionsState
{
    public ConcurrentDictionary<string, List<string>> SubscriptionsByTopic = new();
    public ConcurrentDictionary<string, List<string>> SubscriptionsByAgentType { get; set; } = new();
}