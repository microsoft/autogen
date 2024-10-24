using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Runtime;

internal sealed class WorkerAgentGrain([PersistentState("state", "agent-state")] IPersistentState<AgentState> state) : Grain, IWorkerAgentGrain
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