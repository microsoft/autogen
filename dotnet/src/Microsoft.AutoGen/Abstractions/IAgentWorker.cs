// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorker.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentWorker
{
    ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default);
    ValueTask SendRequest(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask SendResponse(RpcResponse response, CancellationToken cancellationToken = default);
    ValueTask Store(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> Read(AgentId agentId, CancellationToken cancellationToken = default);
}
