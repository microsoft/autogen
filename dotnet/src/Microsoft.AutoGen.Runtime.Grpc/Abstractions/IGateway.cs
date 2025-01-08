// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

public interface IGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    //ValueTask BroadcastEvent(CloudEvent evt);
    ValueTask StoreAsync(Contracts.AgentState value);
    ValueTask<Contracts.AgentState> ReadAsync(AgentId agentId);
    ValueTask<RegisterAgentTypeResponse> RegisterAgentTypeAsync(RegisterAgentTypeRequest request);
    ValueTask<AddSubscriptionResponse> AddSubscriptionAsync(AddSubscriptionRequest request);
}
