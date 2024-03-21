using Microsoft.AI.Agents.Abstractions;

namespace Microsoft.AI.DevTeam.Events
{
    public enum GithubFlowEventType
    {
        NewAsk,
        ReadmeChainClosed,
        CodeChainClosed,
        CodeGenerationRequested,
        DevPlanRequested,
        ReadmeGenerated,
        DevPlanGenerated,
        CodeGenerated,
        DevPlanChainClosed,
        ReadmeRequested,
        ReadmeStored,
        SandboxRunFinished,
        ReadmeCreated,
        CodeCreated,
        DevPlanCreated,
        SandboxRunCreated
    }
}