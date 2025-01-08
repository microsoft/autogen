// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

public interface IGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequestAsync(RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask BroadcastEventAsync(CloudEvent evt, CancellationToken cancellationToken = default);
    ValueTask StoreAsync(Contracts.AgentState value, CancellationToken cancellationToken = default);
    ValueTask<Contracts.AgentState> ReadAsync(AgentId agentId, CancellationToken cancellationToken = default);
    ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request, CancellationToken cancellationToken = default);
    ValueTask<SubscriptionResponse> SubscribeAsync(SubscriptionRequest request, CancellationToken cancellationToken = default);
    ValueTask<SubscriptionResponse> UnsubscribeAsync(SubscriptionRequest request, CancellationToken cancellationToken = default);
    ValueTask<SubscriptionResponse> GetSubscriptionsAsync(Type type, CancellationToken cancellationToken = default);
    Task SendMessageAsync(IConnection connection, CloudEvent cloudEvent, CancellationToken cancellationToken = default);
}
