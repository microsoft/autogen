// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentGrain.cs

using StateDict = System.Collections.Generic.IDictionary<string, object>;

namespace Microsoft.AutoGen.Runtime.Grpc.Abstractions;

internal interface IAgentGrain : IGrainWithStringKey
{
    ValueTask<StateDict> ReadStateAsync();
    ValueTask<string> WriteStateAsync(StateDict state, string eTag);
}
