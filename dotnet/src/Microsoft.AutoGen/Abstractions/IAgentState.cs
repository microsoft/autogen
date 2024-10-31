// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentState.cs

namespace Microsoft.AutoGen.Abstractions;

internal interface IWorkerAgentGrain
{
    ValueTask<AgentState> ReadStateAsync();
    ValueTask<string> WriteStateAsync(AgentState state, string eTag);
}
