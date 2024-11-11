// Copyright (c) Microsoft Corporation. All rights reserved.
// IWorkerAgentGrain.cs

using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime;

internal interface IWorkerAgentGrain : IGrainWithStringKey
{
    ValueTask<AgentState> ReadStateAsync();
    ValueTask<string> WriteStateAsync(AgentState state, string eTag);
}
