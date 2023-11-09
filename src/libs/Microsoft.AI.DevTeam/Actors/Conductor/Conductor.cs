using Microsoft.AI.DevTeam.Skills;
using Orleans.Concurrency;
using Orleans.Runtime;

namespace Microsoft.AI.DevTeam;

public class Conductor : Grain, IOrchestrateWorkflows
{
    private readonly IManageGithub _ghService;
    public Conductor( IManageGithub ghService)
    {
        _ghService = ghService;
    }
     public async Task InitialFlow(string input, string org, string repo, long parentNumber)
    {
            await _ghService.CreateBranch(new CreateBranchRequest
            {
                Org = org,
                Repo = repo,
                Branch = $"sk-{parentNumber}"
            });
            
            var pmIssue = await _ghService.CreateIssue(new CreateIssueRequest
            {
                Label = $"{nameof(PM)}.{nameof(PM.Readme)}",
                Org = org,
                Repo = repo,
                Input = input,
                ParentNumber = parentNumber
            });
            var devLeadIssue = await _ghService.CreateIssue(new CreateIssueRequest
            {
                Label = $"{nameof(DevLead)}.{nameof(DevLead.Plan)}",
                Org = org,
                Repo = repo,
                Input = input,
                ParentNumber = parentNumber
            });
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
        foreach(var prompt in prompts)
        {
            var issue = await _ghService.CreateIssue(new CreateIssueRequest
                            {
                                Label = $"{nameof(Developer)}.{nameof(Developer.Implement)}",
                                Org = org,
                                Repo = repo,
                                Input = prompt,
                                ParentNumber = parentNumber
                            });
            metadataList.Add(new StoreMetadataPairs
            {
                Key = issue.IssueNumber,
                Value = new NewIssueResponse { CommentId = issue.CommentId, IssueNumber = (int)parentNumber}
            });
        }
        await lookup.StoreMetadata(metadataList);
    }
}
