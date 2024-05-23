using System;
using System.Text.Json;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.AI.DevTeam.Events;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class Hubber : Agent
{
     protected override string Namespace => Consts.MainNamespace;
    private readonly IManageGithub _ghService;

    public Hubber(IManageGithub ghService)
    {
        _ghService = ghService;
    }

    public override async Task HandleEvent(Event item)
    {
        ArgumentNullException.ThrowIfNull(item);
        ArgumentNullException.ThrowIfNull(item.Data);

        switch (item.Type)
        {
            case nameof(GithubFlowEventType.NewAsk):
                {
                    var context = item.ToGithubContext();
                    var pmIssue = await CreateIssue(context.Org, context.Repo , item.Data["input"], "PM.Readme", context.IssueNumber);
                    var devLeadIssue = await CreateIssue(context.Org, context.Repo , item.Data["input"], "DevLead.Plan", context.IssueNumber);
                    await PostComment(context.Org, context.Repo, context.IssueNumber, $" - #{pmIssue} - tracks PM.Readme");
                    await PostComment(context.Org, context.Repo, context.IssueNumber, $" - #{devLeadIssue} - tracks DevLead.Plan");   
                    await CreateBranch(context.Org, context.Repo, $"sk-{context.IssueNumber}");
                }
                break;
            case nameof(GithubFlowEventType.ReadmeGenerated):
            case nameof(GithubFlowEventType.DevPlanGenerated):
            case nameof(GithubFlowEventType.CodeGenerated):
            {
                var context = item.ToGithubContext();
                var result = item.Data["result"];
                var contents = string.IsNullOrEmpty(result)? "Sorry, I got tired, can you try again please? ": result;
                await PostComment(context.Org,context.Repo, context.IssueNumber, contents);
            }
                break;
            case nameof(GithubFlowEventType.DevPlanCreated):
                {
                    var context = item.ToGithubContext();
                    var plan = JsonSerializer.Deserialize<DevLeadPlanResponse>(item.Data["plan"]);
                    var prompts = plan.steps.SelectMany(s => s.subtasks.Select(st => st.prompt));
                    
                    foreach (var prompt in prompts)
                    {
                        var functionName = "Developer.Implement";
                        var issue = await CreateIssue(context.Org, context.Repo, prompt, functionName, context.ParentNumber.Value);
                        var commentBody = $" - #{issue} - tracks {functionName}";
                        await PostComment(context.Org, context.Repo, context.ParentNumber.Value, commentBody);
                    }
                }
                break;
            case nameof(GithubFlowEventType.ReadmeStored):
                {
                    var context = item.ToGithubContext();
                    var branch = $"sk-{context.ParentNumber}";
                    await CommitToBranch(context.Org, context.Repo, context.ParentNumber.Value, context.IssueNumber, "output", branch);
                    await CreatePullRequest(context.Org, context.Repo, context.ParentNumber.Value, branch);
                }
                break;
            case nameof(GithubFlowEventType.SandboxRunFinished):
                {
                    var context = item.ToGithubContext();
                    var branch = $"sk-{context.ParentNumber}";
                    await CommitToBranch(context.Org, context.Repo, context.ParentNumber.Value, context.IssueNumber, "output", branch);
                }
                break;
            default:
                break;
        }
    }

    public async Task<int> CreateIssue(string org, string repo, string input, string function, long parentNumber)
    {
        return await _ghService.CreateIssue(org, repo, input, function, parentNumber);
    }
    public async Task PostComment(string org, string repo, long issueNumber, string comment)
    {
        await _ghService.PostComment(org, repo, issueNumber, comment);
    }
    public async Task CreateBranch(string org, string repo, string branch)
    {
        await _ghService.CreateBranch(org, repo, branch);
    }
    public async Task CreatePullRequest(string org, string repo, long issueNumber, string branch)
    {
        await _ghService.CreatePR(org, repo, issueNumber, branch);
    }
    public async Task CommitToBranch(string org, string repo, long parentNumber, long issueNumber, string rootDir, string branch)
    {
        await _ghService.CommitToBranch(org, repo, parentNumber, issueNumber, rootDir, branch);
    }
}