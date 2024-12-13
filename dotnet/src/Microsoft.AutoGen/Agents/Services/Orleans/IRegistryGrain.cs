// Copyright (c) Microsoft Corporation. All rights reserved.
// IRegistryGrain.cs
using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Agents;

public interface IRegistryGrain : IGrainWithIntegerKey
{
    ValueTask<(IGateway? Worker, bool NewPlacement)> GetOrPlaceAgent(AgentId agentId);
    ValueTask RemoveWorker(IGateway worker);
    ValueTask RegisterAgentType(string type, IGateway worker);
    ValueTask AddWorker(IGateway worker);
    ValueTask UnregisterAgentType(string type, IGateway worker);
    ValueTask<IGateway?> GetCompatibleWorker(string type);
}
