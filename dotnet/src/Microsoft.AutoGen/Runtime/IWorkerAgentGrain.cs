using Microsoft.AutoGen.Agents.Abstractions;

namespace Microsoft.AutoGen.Agents.Runtime;

internal interface IWorkerAgentGrain : IGrainWithStringKey
{
    ValueTask<AgentState> ReadStateAsync();
    ValueTask<string> WriteStateAsync(AgentState state, string eTag);
}