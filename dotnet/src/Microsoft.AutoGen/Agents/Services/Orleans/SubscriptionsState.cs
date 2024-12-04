// Copyright (c) Microsoft Corporation. All rights reserved.
// SubscriptionsState.cs
using System.Collections.Concurrent;

namespace Microsoft.AutoGen.Abstractions;
[GenerateSerializer]
[Serializable]
public sealed class SubscriptionsState
{    
    public ConcurrentDictionary<string, Subscription> _subscriptionsByAgentType = new();
    public ConcurrentDictionary<string, List<string>> _subscriptionsByTopic = new();
    public ConcurrentDictionary<string, List<string>> Subscriptions { get; set; } = new();
}