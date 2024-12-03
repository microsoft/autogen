// Copyright (c) Microsoft Corporation. All rights reserved.
// ISubscriptionsGrain.cs

namespace Microsoft.AutoGen.Agents;
public interface ISubscriptionsGrain : IGrainWithIntegerKey
{
    ValueTask SubscribeAsync(string agentType, string topic);
    ValueTask UnsubscribeAsync(string agentType, string topic);
    ValueTask<Dictionary<string, List<string>>> GetSubscriptions(string agentType);
}
