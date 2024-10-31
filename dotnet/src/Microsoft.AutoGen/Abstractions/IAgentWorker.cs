// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorker.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentWorker
{
    ValueTask PublishEventAsync(CloudEvent evt, CancellationToken cancellationToken = default);
    ValueTask SendRequest(IAgentBase agent, RpcRequest request);
    ValueTask SendResponse(RpcResponse response);
    ValueTask Store(AgentState value);
    ValueTask<AgentState> Read(AgentId agentId);
}
