using Orleans.Concurrency;
using Orleans.Runtime;
using Orleans.Streams;
using Orleans.Timers;

namespace Microsoft.AI.DevTeam;

[StatelessWorker]
[ImplicitStreamSubscription("Hubber")]
public class Hubber : Grain, IGrainWithStringKey
{
    private readonly IManageGithub _ghService;

    public Hubber( IManageGithub ghService)
    {
        _ghService = ghService;
    }

    public async override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create("Hubber", this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);

        await stream.SubscribeAsync(HandleEvent);
    }
    public async Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.NewAsk:
                var org = item.Data["org"];
                var repo = item.Data["repo"];
                var input = item.Message;
                var parentNumber = long.Parse(item.Data["parentNumber"]);
                var pmIssue = await CreateIssue(org, repo, input, "", parentNumber);
                var devLeadIssue = await CreateIssue(org, repo, input, "", parentNumber);
                // TODO: store the mapping of parent/child?
                break;
            case EventType.ReadmeGenerated:
                 // _ghService.PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), item.Message);
                break;
            case EventType.DevPlanGenerated:
                // _ghService.PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), item.Message);
                break;
            case EventType.CodeGenerated:
                // _ghService.PostComment(item.Data["org"], item.Data["repo"], long.Parse(item.Data["issueNumber"]), item.Message);
                break;
            case EventType.DevPlanChainClosed:
                // for each step, create Dev issue
                //var devIssues = await CreateIssue(org, repo, input, "", parentNumber);
                break;
            default:
                break;
        }
    }

    public async Task<NewIssueResponse> CreateIssue(string org, string repo, string input, string function, long parentNumber)
    {
        return await _ghService.CreateIssue(org, repo,input,function,parentNumber);
    }
     public async Task PostComment(string org, string repo,long issueNumber, string comment )
    {
        await _ghService.PostComment(org, repo, issueNumber, comment);
    }
     public async Task CreateBranch()
    {
        // await _ghService.CreateBranch();
    }
     public async Task CreatePullRequest()
    {
        // await _ghService.CreatePR();
    }
     public async Task CommitToBranch()
    {
        // await _ghService.CommitToBranch()
    }
}
