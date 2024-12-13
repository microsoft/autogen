// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentStateGrain.cs

using Microsoft.AutoGen.Contracts;

namespace Microsoft.AutoGen.Agents;

internal sealed class AgentStateGrain([PersistentState("state", "AgentStateStore")] IPersistentState<AgentState> state) : Grain, IAgentState
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
}
