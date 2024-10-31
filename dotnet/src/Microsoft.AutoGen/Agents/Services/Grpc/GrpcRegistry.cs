// Copyright (c) Microsoft Corporation. All rights reserved.
// GrpcRegistry.cs

using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Agents;
public class GrpcRegistry : Registry, IAgentRegistry
{
    public ValueTask RegisterAgentType(string type, IGateway worker)
    {
        throw new NotImplementedException();
    }

    public ValueTask UnregisterAgentType(string type, IGateway worker)
    {
        throw new NotImplementedException();
    }

    public ValueTask AddWorker(IGateway worker)
    {
        throw new NotImplementedException();
    }

    public ValueTask RemoveWorker(IGateway worker)
    {
        throw new NotImplementedException();
    }

    public ValueTask<(IGateway? Gateway, bool NewPlacment)> GetOrPlaceAgent(AgentId agentId)
    {
        throw new NotImplementedException();
    }
}