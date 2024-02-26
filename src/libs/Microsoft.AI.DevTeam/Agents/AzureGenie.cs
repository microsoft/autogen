using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
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
        var streamId = StreamId.Create(Consts.MainNamespace, this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);

        await stream.SubscribeAsync(HandleEvent);
    }

    public override async Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case EventType.ReadmeCreated:
                //_azureService.Store();
                // postEvent ReadmeStored
                break;
            case EventType.CodeCreated:
                // _azureService.Store();
                // _azureService.RunInSandbox();
                break;
            default:
                break;
        }
    }
}


