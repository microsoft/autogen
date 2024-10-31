// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentContext.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentContext
{
    AgentId AgentId { get; }
    IAgentBase? AgentInstance { get; set; }
    ValueTask Store(AgentState value);
    ValueTask<AgentState> Read(AgentId agentId);
    ValueTask SendResponseAsync(RpcRequest request, RpcResponse response);
    ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request);
    ValueTask PublishEventAsync(CloudEvent @event);
}
