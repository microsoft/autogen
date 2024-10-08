using Microsoft.Extensions.Hosting;
using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.AutoGen.Agents.Client;
using Runtime = Microsoft.AutoGen.Agents.Runtime;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.AspNetCore.Hosting;

// start the server runtime
var app = await Runtime.Host.StartAsync(true);
// start the client worker
var clientApp = await App.StartAsync<HelloAgent>("HelloAgent");
// get the client
var client = clientApp.Services.GetRequiredService<AgentClient>();

// why doesn't this work?
//await client.PublishEventAsync("HelloAgents", new NewMessageReceived{ Message = "World" })
// instead we have to do this
//send our hello message event via cloud events
var evt = new NewMessageReceived
{
    Message = "World"
}.ToCloudEvent("HelloAgents");
await client.PublishEventAsync(evt);

await clientApp.WaitForShutdownAsync();
await app.WaitForShutdownAsync();

[TopicSubscription("HelloAgents")]
public class HelloAgent(
    IAgentContext context,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : ConsoleAgent(
        context,
        typeRegistry),
        ISayHello,
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>
{
    public async Task Handle(NewMessageReceived item)
    {
        var response = await SayHello(item.Message).ConfigureAwait(false);
        var evt = new Output
        {
            Message = response
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt).ConfigureAwait(false);
        var goodbye = new ConversationClosed
        {
            UserId = this.AgentId.Key,
            UserMessage = "Goodbye"
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(goodbye).ConfigureAwait(false);
    }
    public async Task Handle(ConversationClosed item)
    {
        var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
        var evt = new Output
        {
            Message = goodbye
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt).ConfigureAwait(false);
        throw new NotImplementedException("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^Conversation Closed");
    }
    public async Task<string> SayHello(string ask)
    {
        var response = $"\n\n\n\n***************Hello {ask}**********************\n\n\n\n";
        return response;
    }
}
public interface ISayHello
{
    public Task<string> SayHello(string ask);
}