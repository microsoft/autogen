using Microsoft.AI.Agents.Abstractions;
using Orleans.Streams;

namespace Microsoft.AI.Agents.Orleans;

public abstract class Agent : Grain, IGrainWithStringKey, IAgent
{
    protected abstract string Namespace { get; }
    public abstract Task HandleEvent(Event item);

    private async Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        await HandleEvent(item).ConfigureAwait(true);
    }

    public async Task PublishEvent(Event item)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(ns: "default", key: item.Namespace);
        var stream = streamProvider.GetStream<Event>(streamId);
        await stream.OnNextAsync(item).ConfigureAwait(true);
    }

    public override async Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(Namespace, this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);
        await stream.SubscribeAsync(HandleEvent).ConfigureAwait(true);
    }
}
