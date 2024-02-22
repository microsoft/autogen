using Orleans.Concurrency;
using Orleans.Runtime;
using Orleans.Streams;
using Orleans.Timers;

namespace Microsoft.AI.DevTeam;

[StatelessWorker]
[ImplicitStreamSubscription("AzureGenie")]
public class AzureGenie : Grain, IGrainWithStringKey
{
    private readonly IManageAzure _azureService;

    public AzureGenie( IManageAzure azureService)
    {
        _azureService = azureService;
    }

    public async override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create("AzureGenie", this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);

        await stream.SubscribeAsync(HandleEvent);
    }

    // -> AzureOps
    // -> ReadmeFinished
    //     -> store
    // -> CodeFinished
    //     -> store
    //     -> run in sandbox
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
}
