using Microsoft.Extensions.Hosting;
using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.AutoGen.Agents.Client;
using Microsoft.AutoGen.Agents.Runtime;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;

// start the server runtime
var builder = WebApplication.CreateBuilder(args);
builder.AddLocalAgentService();
var app = builder.Build();
app.MapAgentService();
await app.StartAsync().ConfigureAwait(false);

// start the client worker
var clientBuilder = WebApplication.CreateBuilder(args);
clientBuilder.AddLocalAgentWorker().AddAgent<HelloAgent>("HelloAgent");
var clientApp = clientBuilder.Build();
await clientApp.StartAsync().ConfigureAwait(false);

// get the client
var client = clientApp.Services.GetRequiredService<AgentClient>();

//send our hello message event via cloud events
var evt = new NewMessageReceived
{
    Message = "World"
}.ToCloudEvent("HelloAgents");
await client.PublishEventAsync(evt).ConfigureAwait(false);

await clientApp.WaitForShutdownAsync().ConfigureAwait(false);
await app.WaitForShutdownAsync().ConfigureAwait(false);

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