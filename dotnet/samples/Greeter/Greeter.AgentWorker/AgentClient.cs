using System.Diagnostics;
using Agents;
using Microsoft.AutoGen.Agents.Worker.Client;
using AgentId = Microsoft.AutoGen.Agents.Worker.Client.AgentId;

namespace Greeter.AgentWorker;

public sealed class AgentClient(ILogger<AgentClient> logger, AgentWorkerRuntime runtime, DistributedContextPropagator distributedContextPropagator, EventTypes typeRegistry) : AgentBase(new ClientContext(logger, runtime, distributedContextPropagator), typeRegistry)
{
    public async ValueTask PublishEventAsync(CloudEvent @event) => await PublishEvent(@event);
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
