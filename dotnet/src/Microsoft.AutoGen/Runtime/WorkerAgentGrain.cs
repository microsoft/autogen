using Microsoft.AutoGen.Abstractions;

namespace Microsoft.AutoGen.Runtime;

internal sealed class WorkerAgentGrain([PersistentState("state", "AgentStateStore")] IPersistentState<AgentState> state) : Grain, IWorkerAgentGrain
{
    public async ValueTask<string> WriteStateAsync(AgentState newState, string eTag)
    {
        if (string.Equals(state.Etag, eTag, StringComparison.Ordinal))
        {
            state.State = newState;
            await state.WriteStateAsync();
        }

        return state.Etag;
    }

    public ValueTask<AgentState> ReadStateAsync()
    {
        return ValueTask.FromResult(state.State);
    }
}