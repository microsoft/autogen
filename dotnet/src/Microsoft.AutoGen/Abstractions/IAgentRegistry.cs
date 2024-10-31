// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentRegistry.cs

using Orleans;

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentRegistry : IGrainWithIntegerKey
{
    ValueTask RegisterAgentType(string type, IGateway worker);
    ValueTask UnregisterAgentType(string type, IGateway worker);
    ValueTask AddWorker(IGateway worker);
    ValueTask RemoveWorker(IGateway worker);
    ValueTask<(IGateway? Gateway, bool NewPlacment)> GetOrPlaceAgent(AgentId agentId);
}
