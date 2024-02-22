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
                
                break;
            case EventType.NewAskReadme:
                
                break;
            case EventType.ChainClosed:
                
                break;
            default:
                break;
        }
    }

//     GithubAgent
// -> create issue
// -> comment to issue
// -> create branch
// -> create PR
// -> commit to branch
    public async Task CreateIssue()
    {
        // await _ghService.CreateIssue();
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
