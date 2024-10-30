// Copyright (c) Microsoft. All rights reserved.

using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;
public interface IAgentWorkerRuntime
{
    ValueTask PublishEvent(CloudEvent evt);
    ValueTask SendRequest(IAgentBase agent, RpcRequest request);
    ValueTask SendResponse(RpcResponse response);
    ValueTask Store(AgentState value);
    ValueTask<AgentState> Read(AgentId agentId);
}
