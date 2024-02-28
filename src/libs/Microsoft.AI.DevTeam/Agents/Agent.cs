using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.DevTeam;

public abstract class Agent : Grain, IGrainWithStringKey
{
    public abstract Task HandleEvent(Event item, StreamSequenceToken? token);
    protected async Task PublishEvent(string ns, string id, Event item)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(ns, id);
        var stream = streamProvider.GetStream<Event>(streamId);
        await stream.OnNextAsync(item);
    }

    public async override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(Consts.MainNamespace, this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);

        await stream.SubscribeAsync(HandleEvent);
    }
}
