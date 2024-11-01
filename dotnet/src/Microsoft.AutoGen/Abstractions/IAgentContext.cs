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
    ValueTask Store(AgentState value, CancellationToken cancellationToken = default);
    ValueTask<AgentState> Read(AgentId agentId, CancellationToken cancellationToken = default);
    ValueTask SendResponseAsync(RpcRequest request, RpcResponse response, CancellationToken cancellationToken = default);
    ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken = default);
    ValueTask PublishEventAsync(CloudEvent @event, CancellationToken cancellationToken = default);
}
