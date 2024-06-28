using Agents;
using RpcEvent = Agents.Event;
using Microsoft.Extensions.Logging;

namespace Microsoft.AI.Agents.Worker.Client;

internal sealed class AgentContext(AgentId agentId, AgentWorkerRuntime runtime, ILogger<AgentBase> logger) : IAgentContext
{
    private readonly AgentWorkerRuntime _runtime = runtime;

    public AgentId AgentId { get; } = agentId;
    public ILogger Logger { get; } = logger;
    public AgentBase? AgentInstance { get; set; }

    public async ValueTask SendResponseAsync(RpcRequest request, RpcResponse response)
    {
        response.RequestId = request.RequestId;
        await _runtime.SendResponse(response);
    }

    public async ValueTask SendRequestAsync(AgentBase agent, RpcRequest request)
    {
        await _runtime.SendRequest(agent, request);
    }

    public async ValueTask PublishEventAsync(RpcEvent @event)
    {
        await _runtime.PublishEvent(@event);
    }
}
