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
    public async ValueTask SendResponseAsync(RpcRequest request, RpcResponse response)
    {
        response.RequestId = request.RequestId;
        await _runtime.SendResponse(response);
    }
    public async ValueTask SendRequestAsync(IAgentBase agent, RpcRequest request)
    {
        await _runtime.SendRequest(agent, request).ConfigureAwait(false);
    }
    public async ValueTask PublishEventAsync(CloudEvent @event)
    {
        await _runtime.PublishEvent(@event).ConfigureAwait(false);
    }
    public async ValueTask Store(AgentState value)
    {
        await _runtime.Store(value).ConfigureAwait(false);
    }
    public ValueTask<AgentState> Read(AgentId agentId)
    {
        return _runtime.Read(agentId);
    }
}
