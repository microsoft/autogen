// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentContext.cs

using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

internal sealed class AgentContext(AgentId agentId, IAgentWorkerRuntime runtime, ILogger<AgentBase> logger, DistributedContextPropagator distributedContextPropagator) : IAgentContext
{
    private readonly IAgentWorkerRuntime _runtime = runtime;

    public AgentId AgentId { get; } = agentId;
    public ILogger Logger { get; } = logger;
    public IAgentBase? AgentInstance { get; set; }
    public DistributedContextPropagator DistributedContextPropagator { get; } = distributedContextPropagator;
    public async ValueTask SendResponseAsync(RpcRequest request, RpcResponse response, CancellationToken cancellationToken)
    {
        response.RequestId = request.RequestId;
        await _runtime.SendResponse(response, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request, CancellationToken cancellationToken)
    {
        await _runtime.SendRequest(agent, request, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask PublishEventAsync(CloudEvent @event, CancellationToken cancellationToken)
    {
        await _runtime.PublishEvent(@event, cancellationToken).ConfigureAwait(false);
    }
    public async ValueTask Store(AgentState value, CancellationToken cancellationToken)
    {
        await _runtime.Store(value, cancellationToken).ConfigureAwait(false);
    }
    public ValueTask<AgentState> Read(AgentId agentId, CancellationToken cancellationToken)
    {
        return _runtime.Read(agentId, cancellationToken);
    }
}
