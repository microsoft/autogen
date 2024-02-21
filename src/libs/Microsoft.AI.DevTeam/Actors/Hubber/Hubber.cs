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
    public async Task ScheduleCommitSandboxRun(CommitRequest commitRequest, MarkTaskCompleteRequest markTaskCompleteRequest, SandboxRequest sandboxRequest)
    {
        
    }
}
