// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentStateGrain.cs

using Microsoft.AutoGen.Protobuf;
using Microsoft.AutoGen.Runtime.Grpc.Abstractions;

namespace Microsoft.AutoGen.Runtime.Grpc;

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

internal sealed class AgentStateGrain([PersistentState("state", "AgentStateStore")] IPersistentState<AgentState> state) : Grain, IAgentState, IAgentGrain
{
    /// <inheritdoc />
    public async ValueTask<string> WriteStateAsync(AgentState newState, string eTag, CancellationToken cancellationToken = default)
    {
        // etags for optimistic concurrency control
        // if the Etag is null, its a new state
        // if the passed etag is null or empty, we should not check the current state's Etag - caller doesnt care
        // if both etags are set, they should match or it means that the state has changed since the last read. 
        if ((string.IsNullOrEmpty(state.Etag)) || (string.IsNullOrEmpty(eTag)) || (string.Equals(state.Etag, eTag, StringComparison.Ordinal)))
        {
            state.State = newState;
            await state.WriteStateAsync().ConfigureAwait(false);
        }
        else
        {
            //TODO - this is probably not the correct behavior to just throw - I presume we want to somehow let the caller know that the state has changed and they need to re-read it
            throw new ArgumentException(
                "The provided ETag does not match the current ETag. The state has been modified by another request.");
        }
        return state.Etag;
    }

    /// <inheritdoc />
    public ValueTask<AgentState> ReadStateAsync(CancellationToken cancellationToken = default)
    {
        return ValueTask.FromResult(state.State);
    }

    ValueTask<AgentState> IAgentGrain.ReadStateAsync()
    {
        return ReadStateAsync();
    }

    ValueTask<string> IAgentGrain.WriteStateAsync(AgentState state, string eTag)
    {
        return WriteStateAsync(state, eTag);
    }
}
