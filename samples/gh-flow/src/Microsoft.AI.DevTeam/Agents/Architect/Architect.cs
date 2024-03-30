using Microsoft.AI.Agents.Abstractions;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;


// The architect has Org+Repo scope and is holding the knowledge of the high level architecture of the project
[ImplicitStreamSubscription(Consts.MainNamespace)]
public class Architect : AiAgent<ArchitectState>
{
    protected override string Namespace => Consts.MainNamespace;
    public Architect([PersistentState("state", "messages")] IPersistentState<AgentState<ArchitectState>> state, ISemanticTextMemory memory, Kernel kernel) 
    : base(state, memory, kernel)
    {
    }

    public override Task HandleEvent(Event item, StreamSequenceToken? token)
    {
       return Task.CompletedTask;
    }
}

[GenerateSerializer]
public class ArchitectState
{
    [Id(0)]
    public string FilesTree { get; set; }
    [Id(1)]
    public string HighLevelArchitecture { get; set; }
}