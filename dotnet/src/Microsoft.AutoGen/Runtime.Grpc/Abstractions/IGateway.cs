// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

public interface IConnection
{
}

public interface IGateway : IGrainObserver
{
    ValueTask BroadcastEventAsync(CloudEvent evt);

    ValueTask<RpcResponse> InvokeRequestAsync(RpcRequest request);

    ValueTask StoreAsync(Protobuf.AgentState value);
    ValueTask<Protobuf.AgentState> ReadAsync(Protobuf.AgentId agentId);

    ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(string requestId, RegisterAgentTypeRequest request);

    ValueTask<AddSubscriptionResponse> SubscribeAsync(AddSubscriptionRequest request);
    ValueTask<RemoveSubscriptionResponse> UnsubscribeAsync(RemoveSubscriptionRequest request);
    ValueTask<List<Subscription>> GetSubscriptionsAsync(GetSubscriptionsRequest request);

    Task SendMessageAsync(IConnection connection, CloudEvent cloudEvent);
}
