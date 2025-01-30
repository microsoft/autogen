// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentGrain.cs

using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

internal interface IAgentGrain : IGrainWithStringKey
{
    ValueTask<AgentState> ReadStateAsync();
    ValueTask<string> WriteStateAsync(AgentState state, string eTag);
}
