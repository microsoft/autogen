// Copyright (c) Microsoft Corporation. All rights reserved.
// IWorkerGateway.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IWorkerGateway
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request);
    ValueTask BroadcastEvent(CloudEvent evt);
    ValueTask Store(AgentState value);
    ValueTask<AgentState> Read(AgentId agentId);
}
