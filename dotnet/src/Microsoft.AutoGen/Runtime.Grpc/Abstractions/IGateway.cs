// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

public interface IGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequestAsync(RpcRequest request);
    ValueTask BroadcastEventAsync(CloudEvent evt);
    ValueTask StoreAsync(Contracts.AgentState value);
    ValueTask<Contracts.AgentState> ReadAsync(AgentId agentId);
    ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request);
    ValueTask<AddSubscriptionResponse> SubscribeAsync(AddSubscriptionRequest request);
    ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(RemoveSubscriptionRequest request);
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request);
    Task SendMessageAsync(IConnection connection, CloudEvent cloudEvent);
}
