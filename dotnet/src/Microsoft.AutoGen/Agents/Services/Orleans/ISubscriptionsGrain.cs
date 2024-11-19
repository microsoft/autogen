// Copyright (c) Microsoft Corporation. All rights reserved.
// ISubscriptionsGrain.cs

namespace Microsoft.AutoGen.Agents;
public interface ISubscriptionsGrain : IGrainWithIntegerKey
{
    ValueTask Subscribe(string agentType, string topic);
    ValueTask Unsubscribe(string agentType, string topic);
    ValueTask<Dictionary<string, List<string>>> GetSubscriptions(string agentType);
}
