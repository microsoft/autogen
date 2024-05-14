using Dapr.Actors.Runtime;
using Dapr.Client;
using Microsoft.AI.Agents.Abstractions;

namespace Microsoft.AI.Agents.Dapr;

public abstract class Agent : Actor, IAgent
{
    private readonly DaprClient daprClient;

    protected Agent(ActorHost host, DaprClient daprClient) : base(host)
    {
        this.daprClient = daprClient;
    }
    public abstract Task HandleEvent(Event item);

    public async Task PublishEvent(string ns, string id, Event item)
    {
        var metadata = new Dictionary<string, string>() {
                 { "cloudevent.Type", item.Type },
                 { "cloudevent.Subject",  item.Subject },
                 { "cloudevent.id", Guid.NewGuid().ToString()}
            };
      
       await daprClient.PublishEventAsync(ns, id, item, metadata);
    }
}
