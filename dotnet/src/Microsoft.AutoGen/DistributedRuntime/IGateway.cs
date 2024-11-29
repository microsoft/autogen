// Copyright (c) Microsoft Corporation. All rights reserved.
// IGateway.cs

using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.DistributedRuntime;

public interface IGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    ValueTask BroadcastEvent(CloudEvent evt);
    ValueTask StoreAsync(AgentState value);
    ValueTask<AgentState> ReadAsync(AgentId agentId);
}
