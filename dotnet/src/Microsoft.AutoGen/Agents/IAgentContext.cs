using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents;

public interface IAgentContext
{
    AgentId AgentId { get; }
    AgentBase? AgentInstance { get; set; }
    DistributedContextPropagator DistributedContextPropagator { get; }
    ILogger Logger { get; }
    ValueTask SendResponseAsync(RpcRequest request, RpcResponse response);
    ValueTask SendRequestAsync(AgentBase agent, RpcRequest request);
    ValueTask PublishEventAsync(CloudEvent @event);
}
