namespace Microsoft.AutoGen.Runtime;

internal sealed class AgentStateGrain([PersistentState("state", "agent-state")] IPersistentState<Dictionary<string, object>> state) : Grain, IAgentStateGrain
{
    public ValueTask<(Dictionary<string, object> State, string ETag)> ReadStateAsync()
    {
        return new((state.State, state.Etag));
    }

    public async ValueTask<string> WriteStateAsync(Dictionary<string, object> value, string eTag)
    {
        if (string.Equals(state.Etag, eTag, StringComparison.Ordinal))
        {
            state.State = value;
            await state.WriteStateAsync();
        }

        return state.Etag;
    }
}
