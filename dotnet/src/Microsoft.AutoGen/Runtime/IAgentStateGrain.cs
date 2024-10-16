namespace Microsoft.AutoGen.Runtime;

internal interface IAgentStateGrain : IGrainWithStringKey
{
    ValueTask<(Dictionary<string, object> State, string ETag)> ReadStateAsync();
    ValueTask<string> WriteStateAsync(Dictionary<string, object> state, string eTag);
}
