using Agents;
using RpcEvent = Agents.Event;
using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Microsoft.AI.Agents.Worker.Client;

public interface IAgentContext
{
    AgentId AgentId { get; }
    AgentBase? AgentInstance { get; set; }
    DistributedContextPropagator DistributedContextPropagator { get; }
    ILogger Logger { get; }
    ValueTask SendResponseAsync(RpcRequest request, RpcResponse response);
    ValueTask SendRequestAsync(AgentBase agent, RpcRequest request);
    ValueTask PublishEventAsync(RpcEvent @event);
}
