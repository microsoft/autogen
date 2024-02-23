using Orleans.Concurrency;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

[StatelessWorker]
[ImplicitStreamSubscription("AzureGenie")]
public class AzureGenie : Agent
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

    public override async Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.ReadmeChainClosed:
                //_azureService.Store();
                // postEvent ReadmeStored
                break;
            case EventType.CodeChainClosed:
                // _azureService.Store();
                // _azureService.RunInSandbox();
                break;
            default:
                break;
        }
    }
}


