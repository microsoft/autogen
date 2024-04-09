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
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.NewAsk):
                {
                    var parentNumber = long.Parse(item.Data["issueNumber"]);
                    var pmIssue = await CreateIssue(item.Data["org"], item.Data["repo"], item.Message, "PM.Readme", parentNumber);
                    var devLeadIssue = await CreateIssue(item.Data["org"], item.Data["repo"], item.Message, "DevLead.Plan", parentNumber);
                    await PostComment(item.Data["org"], item.Data["repo"], parentNumber, $" - #{pmIssue} - tracks PM.Readme");
                    await PostComment(item.Data["org"], item.Data["repo"], parentNumber, $" - #{devLeadIssue} - tracks DevLead.Plan");   
                    await CreateBranch(item.Data["org"], item.Data["repo"], $"sk-{parentNumber}");
                }
                break;
            case nameof(GithubFlowEventType.ReadmeGenerated):
            case nameof(GithubFlowEventType.DevPlanGenerated):
            case nameof(GithubFlowEventType.CodeGenerated):
                var contents = string.IsNullOrEmpty(item.Message)? "Sorry, I got tired, can you try again please? ": item.Message;
                await PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), contents);
                break;
            case nameof(GithubFlowEventType.DevPlanCreated):
                {
                    var plan = JsonSerializer.Deserialize<DevLeadPlanResponse>(item.Data["plan"]);
                    var prompts = plan.steps.SelectMany(s => s.subtasks.Select(st => st.prompt));
                    var parentNumber = long.Parse(item.Data["parentNumber"]);
                    foreach (var prompt in prompts)
                    {
                        var functionName = "Developer.Implement";
                        var issue = await CreateIssue(item.Data["org"], item.Data["repo"], prompt, functionName, parentNumber);
                        var commentBody = $" - #{issue} - tracks {functionName}";
                        await PostComment(item.Data["org"], item.Data["repo"], parentNumber, commentBody);
                    }
                }
                break;
            case nameof(GithubFlowEventType.ReadmeStored):
                {
                    var parentNumber = long.Parse(item.Data["parentNumber"]);
                    var issueNumber = long.Parse(item.Data["issueNumber"]);
                    var branch = $"sk-{parentNumber}";
                    await CommitToBranch(item.Data["org"], item.Data["repo"], parentNumber, issueNumber, "output", branch);
                    await CreatePullRequest(item.Data["org"], item.Data["repo"], parentNumber, branch);
                }
                break;
            case nameof(GithubFlowEventType.SandboxRunFinished):
                {
                    var parentNumber = long.Parse(item.Data["parentNumber"]);
                    var issueNumber = long.Parse(item.Data["issueNumber"]);
                    var branch = $"sk-{parentNumber}";
                    await CommitToBranch(item.Data["org"], item.Data["repo"], parentNumber, issueNumber, "output", branch);
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