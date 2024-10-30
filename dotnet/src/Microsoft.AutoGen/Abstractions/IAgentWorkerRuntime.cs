// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentWorkerRuntime.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentWorkerRuntime
{
    ValueTask PublishEvent(CloudEvent evt);
    ValueTask SendRequest(IAgentBase agent, RpcRequest request);
    ValueTask SendResponse(RpcResponse response);
    ValueTask Store(AgentState value);
    ValueTask<AgentState> Read(AgentId agentId);
}
