using System.Diagnostics;
using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Agents.Client;

// TODO: Extract this to be part of the Client
public sealed class AgentClient(ILogger<AgentClient> logger, AgentWorkerRuntime runtime, DistributedContextPropagator distributedContextPropagator,
    [FromKeyedServices("EventTypes")] EventTypes eventTypes)
    : AgentBase(new ClientContext(logger, runtime, distributedContextPropagator), eventTypes)
{
    public async ValueTask PublishEventAsync(CloudEvent evt) => await PublishEvent(evt);
    public async ValueTask<RpcResponse> SendRequestAsync(AgentId target, string method, Dictionary<string, string> parameters) => await RequestAsync(target, method, parameters);

    private sealed class ClientContext(ILogger<AgentClient> logger, AgentWorkerRuntime runtime, DistributedContextPropagator distributedContextPropagator) : IAgentContext
    {
        public AgentId AgentId { get; } = new AgentId("client", Guid.NewGuid().ToString());
        public AgentBase? AgentInstance { get; set; }
        public ILogger Logger { get; } = logger;
        public DistributedContextPropagator DistributedContextPropagator { get; } = distributedContextPropagator;

        public async ValueTask PublishEventAsync(CloudEvent @event)
        {
            await runtime.PublishEvent(@event).ConfigureAwait(false);
        }

        public async ValueTask SendRequestAsync(AgentBase agent, RpcRequest request)
        {
            await runtime.SendRequest(AgentInstance!, request).ConfigureAwait(false);
        }

        public async ValueTask SendResponseAsync(RpcRequest request, RpcResponse response)
        {
            await runtime.SendResponse(response).ConfigureAwait(false);
        }
    }
}
