// Copyright (c) Microsoft Corporation. All rights reserved.
// RuntimeAgent.cs

using System.Data;
using Microsoft.AutoGen.Runtime.Grpc.Abstractions;

namespace Microsoft.AutoGen.Runtime.Grpc;

internal sealed class RuntimeAgent([PersistentState("state", "AgentStateStore")] IPersistentState<Contracts.AgentState> state) : Grain, IAgentGrain
{
    /// <inheritdoc />
    public async ValueTask<string> WriteStateAsync(Contracts.AgentState newState, string eTag/*, CancellationToken cancellationToken = default*/)
    {
        // etags for optimistic concurrency control
        // if the Etag is null, its a new state
        // if the passed etag is null or empty, we should not check the current state's Etag - caller doesnt care
        // if both etags are set, they should match or it means that the state has changed since the last read. 
        if (string.IsNullOrEmpty(state.Etag) || string.IsNullOrEmpty(eTag) || string.Equals(state.Etag, eTag, StringComparison.Ordinal))
        {
            state.State = newState;
            await state.WriteStateAsync().ConfigureAwait(false);
        }
        else
        {
            //TODO - this is probably not the correct behavior to just throw - I presume we want to somehow let the caller know that the state has changed and they need to re-read it
            throw new DBConcurrencyException(
                "The provided ETag does not match the current ETag. The state has been modified by another request.");
        }
        return state.Etag;
    }

    /// <inheritdoc />
    public ValueTask<Contracts.AgentState> ReadStateAsync(/*CancellationToken cancellationToken = default*/)
    {
        return ValueTask.FromResult(state.State);
    }
}
