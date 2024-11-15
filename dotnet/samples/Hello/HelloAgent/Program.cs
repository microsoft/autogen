// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Host = Microsoft.Extensions.Hosting.Host;

var builder = Host.CreateApplicationBuilder();

// step 1: create in-memory agent runtime
// step 2: register HelloAgent to that agent runtime
builder
    .AddAgentService(local: true, useGrpc: false)
    .AddAgentWorker(local: true)
    .AddAgent<HelloAgent>("HelloAgent");

// step 3: wait for the agent runtime to shutdown
var app = builder.Build();
await app.StartAsync();

var client = app.Services.GetRequiredService<Client>();
await client.PublishEventAsync("HelloAgents", new NewMessageReceived
{
    Message = "World"
}, new CancellationToken());

await app.WaitForShutdownAsync();

[TopicSubscription("HelloAgents")]
public class HelloAgent(
    IAgentRuntime context, IHostApplicationLifetime hostApplicationLifetime,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : AgentBase(
        context,
        typeRegistry),
        ISayHello,
        IHandleConsole,
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>
{
    public async Task Handle(NewMessageReceived item)
    {
        var response = await SayHello(item.Message);
        var evt = new Output { Message = response };
        await PublishMessageAsync(evt);
        var goodbye = new ConversationClosed
        {
            UserId = this.AgentId.Key,
            UserMessage = "Goodbye"
        };
        await PublishMessageAsync(goodbye);
    }
    public async Task Handle(ConversationClosed item)
    {
        var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
        var evt = new Output
        {
            Message = goodbye
        };
        await PublishMessageAsync(evt);

        // Signal shutdown.
        hostApplicationLifetime.StopApplication();
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
