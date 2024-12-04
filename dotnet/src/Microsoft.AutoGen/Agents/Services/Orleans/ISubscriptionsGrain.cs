// Copyright (c) Microsoft Corporation. All rights reserved.
// ISubscriptionsGrain.cs

using System.Collections.Concurrent;

namespace Microsoft.AutoGen.Agents;
public interface ISubscriptionsGrain : IGrainWithIntegerKey
{
    [Alias("SubscribeAsync")]
    ValueTask SubscribeAsync(string agentType, string topic);
    [Alias("UnsubscribeAsync")]
    ValueTask UnsubscribeAsync(string agentType, string topic);
    [Alias("GetSubscriptionsAsync")]
    ValueTask<ConcurrentDictionary<string, List<string>>> GetSubscriptionsAsync(string? agentType = null);
}
