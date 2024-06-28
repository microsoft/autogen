using Agents;
using Microsoft.AI.Agents.Worker.Client;
using AgentId = Microsoft.AI.Agents.Worker.Client.AgentId;

namespace Greeter.AgentWorker;

internal sealed class Client(ILogger<Client> logger, AgentWorkerRuntime runtime) : AgentBase(new ClientContext(logger, runtime))
{
    private sealed class ClientContext(ILogger<Client> logger, AgentWorkerRuntime runtime) : IAgentContext
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
