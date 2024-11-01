// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorkerRuntime.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentWorkerRuntime
{
    ValueTask PublishEvent(CloudEvent evt, CancellationToken cancellationToken);
    ValueTask SendRequest(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken);
    ValueTask SendResponse(RpcResponse response, CancellationToken cancellationToken);
    ValueTask Store(AgentState value, CancellationToken cancellationToken);
    ValueTask<AgentState> Read(AgentId agentId, CancellationToken cancellationToken);
}
