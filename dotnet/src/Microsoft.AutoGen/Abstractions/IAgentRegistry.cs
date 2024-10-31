// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentRegistry.cs

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentRegistry
{
    ValueTask RegisterAgentType(string type, IWorkerGateway worker);
    ValueTask UnregisterAgentType(string type, IWorkerGateway worker);
    ValueTask AddWorker(IWorkerGateway worker);
    ValueTask RemoveWorker(IWorkerGateway worker);
    ValueTask<(IWorkerGateway? Gateway, bool NewPlacment)> GetOrPlaceAgent(AgentId agentId);
}
