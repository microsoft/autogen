using Microsoft.Extensions.Hosting;
using Microsoft.AutoGen.Agents.Abstractions;
using Microsoft.AutoGen.Agents.Client;
using Microsoft.AutoGen.Agents.Runtime;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Server.Kestrel.Core;

// start the server runtime
var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(serverOptions =>
                {
                    serverOptions.ListenLocalhost(5001, listenOptions =>
                    {
                        listenOptions.Protocols = HttpProtocols.Http2;
                        listenOptions.UseHttps();
                    });
                });
builder.AddAgentService();
builder.UseOrleans(siloBuilder =>
{
    siloBuilder.UseLocalhostClustering(); ;
});
var app = builder.Build();
app.MapAgentService();
await app.StartAsync();

// start the client worker
var clientBuilder = WebApplication.CreateBuilder(args);
clientBuilder.Services.AddHostedService<AgentWorkerRuntime>();
clientBuilder.Services.AddSingleton<AgentClient>();
var agentBuilder = clientBuilder.AddAgentWorker("https://localhost:5001");
var clientApp = clientBuilder.Build();
await clientApp.StartAsync();

// get the client and send a message
AgentClient client = clientApp.Services.GetRequiredService<AgentClient>();

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
        var response = await SayHello(item.Message);
        var evt = new Output
        {
            Message = response
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public async Task Handle(ConversationClosed item)
    {
        var goodbye = "Goodbye!";
        var evt = new Output
        {
            Message = goodbye
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt);
    }

    public async Task<string> SayHello(string ask)
    {
        var response = $"Hello {ask}";
        return response;
    }
}
public interface ISayHello
{
    public Task<string> SayHello(string ask);
}