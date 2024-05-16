using Microsoft.AI.Agents.Abstractions;
using Orleans.Runtime;
using Orleans.Streams;

namespace Microsoft.AI.Agents.Orleans;

public abstract class Agent : Grain, IGrainWithStringKey, IAgent
{
    protected virtual string Namespace { get;set;}
     public abstract Task HandleEvent(Event item);

    private async Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        await HandleEvent(item);
    }
    
    public async Task PublishEvent(string ns, string id, Event item)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(ns, id);
        var stream = streamProvider.GetStream<Event>(streamId);
        await stream.OnNextAsync(item);
    }

    public async override Task OnActivateAsync(CancellationToken cancellationToken)
    {
        var streamProvider = this.GetStreamProvider("StreamProvider");
        var streamId = StreamId.Create(Namespace, this.GetPrimaryKeyString());
        var stream = streamProvider.GetStream<Event>(streamId);
        await stream.SubscribeAsync(HandleEvent);
    }
}
