// Copyright (c) Microsoft Corporation. All rights reserved.
// ISubscriptionsGrain.cs

namespace Microsoft.AutoGen.Agents;
public interface ISubscriptionsGrain : IGrainWithIntegerKey
{
    [Alias("SubscribeAsync")]
    ValueTask SubscribeAsync(string agentType, string topic);
    [Alias("UnsubscribeAsync")]
    ValueTask UnsubscribeAsync(string agentType, string topic);
    [Alias("GetSubscriptions")]
    ValueTask<Dictionary<string, List<string>>> GetSubscriptions(string? agentType = null);
}
