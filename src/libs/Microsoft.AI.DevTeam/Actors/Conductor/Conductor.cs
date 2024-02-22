using Microsoft.AI.DevTeam.Skills;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

public class Conductor : Grain, IOrchestrateWorkflows
{
    private readonly IManageGithub _ghService;

    public Conductor(IManageGithub ghService)
    {
        _ghService = ghService;
    }

    public async Task InitialFlow(string input, string org, string repo, long parentNumber)
    {
        await _ghService.CreateBranch(org, repo, $"sk-{parentNumber}");

        var pmIssue = await _ghService.CreateIssue(org, repo, input, $"{nameof(PM)}.{nameof(PM.Readme)}", parentNumber);
        var devLeadIssue = await _ghService.CreateIssue(org, repo, input, $"{nameof(DevLead)}.{nameof(DevLead.Plan)}", parentNumber);
        var suffix = $"{org}-{repo}";
        var lookup = GrainFactory.GetGrain<ILookupMetadata>(suffix);

        var metadataList = new List<StoreMetadataPairs>{
                new StoreMetadataPairs
                {
                    Key = pmIssue.IssueNumber,
                    Value = new NewIssueResponse { CommentId = pmIssue.CommentId, IssueNumber = (int)parentNumber}
                },
                new StoreMetadataPairs
                {
                    Key = devLeadIssue.IssueNumber,
                    Value = new NewIssueResponse { CommentId = devLeadIssue.CommentId, IssueNumber = (int)parentNumber}
                }
            };
        await lookup.StoreMetadata(metadataList);

        //  await githubActor.CreatePR(); // TODO: this should happen when all tasks are done?
    }
    public async Task ImplementationFlow(DevLeadPlanResponse plan, string org, string repo, int parentNumber)
    {
        var suffix = $"{org}-{repo}";
        var prompts = plan.steps.SelectMany(s => s.subtasks.Select(st => st.prompt));
        var lookup = GrainFactory.GetGrain<ILookupMetadata>(suffix);
        var metadataList = new List<StoreMetadataPairs>();
        foreach (var prompt in prompts)
        {
            var issue = await _ghService.CreateIssue(org, repo, prompt, $"{nameof(Developer)}.{nameof(Developer.Implement)}", parentNumber);
            metadataList.Add(new StoreMetadataPairs
            {
                Key = issue.IssueNumber,
                Value = new NewIssueResponse { CommentId = issue.CommentId, IssueNumber = (int)parentNumber }
            });
        }
        await lookup.StoreMetadata(metadataList);
    }
}

/*
Events:

NewAsk - Org, Repo, IssueNumber

-> PM subscribes -> check label, 
                    if Do It, create an issue, mark it as PM.Readme
                    if PM.Readme send the prompt and create a comment
-> DevLead subscribes -> check label,
                        if Do It, create an issue, mark it as Devlead.Plan
                        if DevLead.Plan, send the prompt and create a comment
-> Developer subscribes -> check label,
                          if Developer.Implement, send the prompt and create a comment

ChainClosed - Org, Repo, IssueNumber

-> PM subscribes -> check label,
                    if PM.Readme send ReadmeCreated event
-> DevLead subscribes -> check label,
                        if DevLead.Plan, send PlanSubstepCreated event

-> Developer subscribes -> check label,
                          if Developer.Implement, send ImplementSubstepCreated event

PlanSubstepCreated - Org, Repo, IssueNumber, Substep

-> Developer subscribes -> create an issue, mark it as Developer.Implement


ReadmeCreated - store readme, commit to PR branch

ImplementSubstepCreated - store code, run in sandbox, commit to PR branch

*/