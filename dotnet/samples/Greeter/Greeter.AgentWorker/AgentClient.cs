using Agents;
using Microsoft.AI.Agents.Worker.Client;
using AgentId = Microsoft.AI.Agents.Worker.Client.AgentId;

namespace Greeter.AgentWorker;

public sealed class AgentClient(ILogger<AgentClient> logger, AgentWorkerRuntime runtime) : AgentBase(new ClientContext(logger, runtime))
{
    public async ValueTask PublishEventAsync(Event @event) => await PublishEvent(@event);
    public async ValueTask<RpcResponse> SendRequestAsync(AgentId target, string method, Dictionary<string, string> parameters) => await RequestAsync(target, method, parameters);

    private sealed class ClientContext(ILogger<AgentClient> logger, AgentWorkerRuntime runtime) : IAgentContext
    {
        public AgentId AgentId { get; } = new AgentId("client", Guid.NewGuid().ToString());
        public AgentBase? AgentInstance { get; set; }
        public ILogger Logger { get; } = logger;

        public async ValueTask PublishEventAsync(Event @event)
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
