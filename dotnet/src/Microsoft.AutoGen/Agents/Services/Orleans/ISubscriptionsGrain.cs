// Copyright (c) Microsoft Corporation. All rights reserved.
// ISubscriptionsGrain.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;

[Alias("Microsoft.AutoGen.Agents.ISubscriptionsGrain")]
public interface ISubscriptionsGrain : IGrainWithIntegerKey
{
    [Alias("SubscribeAsync")]
    ValueTask SubscribeAsync(string agentType, string topic);
    [Alias("UnsubscribeAsync")]
    ValueTask UnsubscribeAsync(string agentType, string topic);
    [Alias("GetSubscriptionsAsync")]
    ValueTask<ConcurrentDictionary<string, List<string>>> GetSubscriptionsByAgentTypeAsync(string? agentType = null);
    [Alias ("GetSubscriptionsByTopicAsync")]
    ValueTask<ConcurrentDictionary<string, List<string>>> GetSubscriptionsByTopicAsync(string? topic = null);
    [Alias("GetSubscriptionsByAgentTypeAsync")]
    ValueTask<SubscriptionsState> GetSubscriptionsStateAsync();
    [Alias("WriteSubscriptionsStateAsync")]
    ValueTask WriteSubscriptionsStateAsync(SubscriptionsState subscriptionsState);
}
