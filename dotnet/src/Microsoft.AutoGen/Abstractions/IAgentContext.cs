// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentContext.cs

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentContext
{
    AgentId AgentId { get; }
    IAgentBase? AgentInstance { get; set; }
    DistributedContextPropagator DistributedContextPropagator { get; } // TODO: Remove this. An abstraction should not have a dependency on DistributedContextPropagator.
    ILogger Logger { get; } // TODO: Remove this. An abstraction should not have a dependency on ILogger.
    ValueTask Store(AgentState value);
    ValueTask<AgentState> Read(AgentId agentId);
    ValueTask SendResponseAsync(RpcRequest request, RpcResponse response);
    ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request);
    ValueTask PublishEventAsync(CloudEvent @event);
}
