// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentGrain.cs
using Microsoft.AutoGen.Protobuf;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Abstractions;
/// <summary>
/// Interface for managing agent state as an Orleans Grain.
/// </summary>
internal interface IAgentGrain : IGrainWithStringKey
{
    /// <summary>
    /// Reads the state from the Orleans Grain.
    /// </summary>
    /// <returns>A task representing the AgentState object</returns>
    ValueTask<AgentState> ReadStateAsync();
    /// <summary>
    /// Writes the state to the Orleans Grain.
    /// </summary>
    /// <param name="state"></param>
    /// <param name="eTag">used for optimistic concurrency control</param>
    /// <returns></returns>
    ValueTask<string> WriteStateAsync(AgentState state, string eTag);
}
