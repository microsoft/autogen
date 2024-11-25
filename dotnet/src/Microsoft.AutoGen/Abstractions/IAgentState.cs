// Copyright (c) Microsoft Corporation. All rights reserved.
// IAgentState.cs

namespace Microsoft.AutoGen.Abstractions;

/// <summary>
/// Interface for managing the state of an agent.
/// </summary>
public interface IAgentState
{
    /// <summary>
    /// Reads the current state of the agent asynchronously.
    /// </summary>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous read operation. The task result contains the current state of the agent.</returns>
    ValueTask<AgentState> ReadStateAsync(CancellationToken cancellationToken = default);

    /// <summary>
    /// Writes the specified state of the agent asynchronously.
    /// </summary>
    /// <param name="state">The state to write.</param>
    /// <param name="eTag">The ETag for concurrency control.</param>
    /// <param name="cancellationToken">A token to cancel the operation.</param>
    /// <returns>A task that represents the asynchronous write operation. The task result contains the ETag of the written state.</returns>
    ValueTask<string> WriteStateAsync(AgentState state, string eTag, CancellationToken cancellationToken = default);
}
