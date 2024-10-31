// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentState.cs
using Orleans;

namespace Microsoft.AutoGen.Abstractions;

public interface IAgentState : IAgentRegistry, IGrainWithStringKey
{
    ValueTask<AgentState> ReadStateAsync();
    ValueTask<string> WriteStateAsync(AgentState state, string eTag);
}
