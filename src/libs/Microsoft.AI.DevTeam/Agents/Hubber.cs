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
                var parentNumber = long.Parse(item.Data["issueNumber"]);
                var pmIssue = await CreateIssue(item.Data["org"], item.Data["repo"], item.Message, $"{nameof(PM)}.{nameof(PM.Readme)}", parentNumber);
                var devLeadIssue = await CreateIssue(item.Data["org"], item.Data["repo"], item.Message, $"{nameof(DevLead)}.{nameof(DevLead.Plan)}", parentNumber);
                // TODO: store the mapping of parent/child?
                await CreateBranch(item.Data["org"], item.Data["repo"], $"sk-{parentNumber}");
                break;
            case EventType.ReadmeGenerated:
            case EventType.DevPlanGenerated:
            case EventType.CodeGenerated:
                await PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), item.Message);
                break;
            case EventType.DevPlanCreated:
                var plan = JsonSerializer.Deserialize<DevLeadPlanResponse>(item.Data["plan"]);
                var devTasks = plan.steps.SelectMany(s => s.subtasks.Select(st => st.prompt)).Select(p =>
                    CreateIssue(item.Data["org"], item.Data["repo"], p, $"{nameof(Developer)}.{nameof(Developer.Implement)}", long.Parse(item.Data["parentNumber"])));
                Task.WaitAll(devTasks.ToArray());
                break;
            case EventType.ReadmeStored:
                await CommitToBranch();
                await CreatePullRequest();
                break;
            case EventType.SandboxRunFinished:
                await CommitToBranch();
                break;
            default:
                break;
        }
    }

    public async Task<NewIssueResponse> CreateIssue(string org, string repo, string input, string function, long parentNumber)
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
    public async Task CreatePullRequest()
    {
        //await _ghService.CreatePR();
    }
    public async Task CommitToBranch()
    {
        //await _ghService.CommitToBranch()
    }
}
