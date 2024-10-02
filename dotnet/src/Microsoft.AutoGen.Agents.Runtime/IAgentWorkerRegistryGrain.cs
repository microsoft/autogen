using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Runtime;

public interface IAgentWorkerRegistryGrain : IGrainWithIntegerKey
{
    ValueTask RegisterAgentType(string type, IWorkerGateway worker);
    ValueTask UnregisterAgentType(string type, IWorkerGateway worker);
    ValueTask AddWorker(IWorkerGateway worker);
    ValueTask RemoveWorker(IWorkerGateway worker);
    ValueTask<(IWorkerGateway? Gateway, bool NewPlacment)> GetOrPlaceAgent(AgentId agentId);
}
