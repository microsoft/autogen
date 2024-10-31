// Copyright (c) Microsoft Corporation. All rights reserved.
// IWorkerGateway.cs

using Orleans;

namespace Microsoft.AutoGen.Abstractions;

public interface IGateway : IGrainObserver
{
    ValueTask<RpcResponse> InvokeRequest(RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask BroadcastEvent(CloudEvent evt, CancellationToken cancellationToken = default);
    ValueTask Store(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> Read(AgentId agentId, CancellationToken cancellationToken = default);
}
