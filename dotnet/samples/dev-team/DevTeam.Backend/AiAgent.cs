// Copyright (c) Microsoft Corporation. All rights reserved.
// AiAgent.cs

using Microsoft.AutoGen.Core;

namespace DevTeam.Agents;

public class AiAgent<T> : Agent
{
    public AiAgent(AgentsMetadata eventTypes, ILogger<AiAgent<T>> logger) : base(eventTypes, logger)
    {
    }

    protected async Task AddKnowledge(string instruction, string v)
    {
        throw new NotImplementedException();
    }

    protected async Task<string> CallFunction(string prompt)
    {
        throw new NotImplementedException();
    }
}
