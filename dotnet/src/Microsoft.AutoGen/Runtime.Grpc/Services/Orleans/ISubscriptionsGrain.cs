// Copyright (c) Microsoft Corporation. All rights reserved.
// ISubscriptionsGrain.cs

namespace Microsoft.AutoGen.Runtime.Grpc;
public interface ISubscriptionsGrain : IGrainWithIntegerKey
{
    ValueTask AddSubscriptionAsync(string agentType, string topic);
    ValueTask RemoveSubscriptionAsync(string agentType, string topic);
    ValueTask<Dictionary<string, List<string>>> GetSubscriptions(string agentType);
}
