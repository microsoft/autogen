using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime;

internal sealed class WorkerAgentGrain([PersistentState("state", "AgentStateStore")] IPersistentState<AgentState> state) : Grain, IWorkerAgentGrain
{
    public async ValueTask<string> WriteStateAsync(AgentState newState, string eTag)
    {
        // if the Etag is null, its a new state
        // if the Etag is not null, it should match the current state's Etag
        if ((string.IsNullOrEmpty(state.Etag)) || (string.Equals(state.Etag, eTag, StringComparison.Ordinal)))
        {
            state.State = newState;
            await state.WriteStateAsync();
        }
        else
        {
            //TODO - this is probably not the correct behavior to just throw - I presume we want to somehow let the caller know that the state has changed and they need to re-read it
            throw new ArgumentException(
                "The provided ETag does not match the current ETag. The state has been modified by another request.");
        }

        return state.Etag;
    }

    public ValueTask<AgentState> ReadStateAsync()
    {
        return ValueTask.FromResult(state.State);
    }
}