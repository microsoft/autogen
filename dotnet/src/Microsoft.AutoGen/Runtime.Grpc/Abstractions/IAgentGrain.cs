// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentGrain.cs

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

internal interface IAgentGrain : IGrainWithStringKey
{
    ValueTask<Contracts.AgentState> ReadStateAsync();
    ValueTask<string> WriteStateAsync(Contracts.AgentState state, string eTag);
}
