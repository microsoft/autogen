using System.Text.Json;
using Microsoft.AI.DevTeam.Skills;
using Octokit;
using Orleans.Concurrency;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class Hubber : Agent
{
    private readonly IManageGithub _ghService;

    public Hubber(IManageGithub ghService)
    {
        _ghService = ghService;
    }

    public async override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(Consts.MainNamespace, this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);

        await stream.SubscribeAsync(HandleEvent);
    }
    public override async Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.NewAsk:
                {
                    var parentNumber = long.Parse(item.Data["issueNumber"]);
                    var pmIssue = await CreateIssue(item.Data["org"], item.Data["repo"], item.Message, $"{nameof(PM)}.{nameof(PM.Readme)}", parentNumber);
                    var devLeadIssue = await CreateIssue(item.Data["org"], item.Data["repo"], item.Message, $"{nameof(DevLead)}.{nameof(DevLead.Plan)}", parentNumber);
                    await PostComment(item.Data["org"], item.Data["repo"], parentNumber, $" - #{pmIssue} - tracks {nameof(PM)}.{nameof(PM.Readme)}");
                    await PostComment(item.Data["org"], item.Data["repo"], parentNumber, $" - #{devLeadIssue} - tracks {nameof(DevLead)}.{nameof(DevLead.Plan)}");   
                    await CreateBranch(item.Data["org"], item.Data["repo"], $"sk-{parentNumber}");
                }
                break;
            case EventType.ReadmeGenerated:
            case EventType.DevPlanGenerated:
            case EventType.CodeGenerated:
                await PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), item.Message);
                break;
            case EventType.DevPlanCreated:
                {
                    var plan = JsonSerializer.Deserialize<DevLeadPlanResponse>(item.Data["plan"]);
                    var prompts = plan.steps.SelectMany(s => s.subtasks.Select(st => st.prompt));
                    var parentNumber = long.Parse(item.Data["parentNumber"]);
                    foreach (var prompt in prompts)
                    {
                        var functionName = $"{nameof(Developer)}.{nameof(Developer.Implement)}";
                        var issue = await CreateIssue(item.Data["org"], item.Data["repo"], prompt, functionName, parentNumber);
                        var commentBody = $" - #{issue} - tracks {functionName}";
                        await PostComment(item.Data["org"], item.Data["repo"], parentNumber, commentBody);
                    }
                }
                break;
            case EventType.ReadmeStored:
                {
                    var parentNumber = long.Parse(item.Data["parentNumber"]);
                    var issueNumber = long.Parse(item.Data["issueNumber"]);
                    var branch = $"sk-{parentNumber}";
                    await CommitToBranch(item.Data["org"], item.Data["repo"], parentNumber, issueNumber, "output", branch);
                    await CreatePullRequest(item.Data["org"], item.Data["repo"], parentNumber, branch);
                }
                break;
            case EventType.SandboxRunFinished:
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
