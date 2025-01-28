// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

public interface IGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequestAsync(RpcRequest request);
    ValueTask BroadcastEventAsync(CloudEvent evt);
    ValueTask StoreAsync(AgentState value);
    ValueTask<AgentState> ReadAsync(Protobuf.AgentId agentId);
    ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request);
    ValueTask<AddSubscriptionResponse> AddSubscriptionAsync(AddSubscriptionRequest request);
    ValueTask<RemoveSubscriptionResponse> RemoveSubscriptionAsync(RemoveSubscriptionRequest request);
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request);
    Task SendMessageAsync(IConnection connection, CloudEvent cloudEvent);
}
