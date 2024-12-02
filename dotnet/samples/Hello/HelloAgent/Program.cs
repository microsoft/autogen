// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Hello.Events;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

// step 1: create in-memory agent runtime

// step 2: register HelloAgent to that agent runtime

// step 3: start the agent runtime

// step 4: send a message to the agent

// step 5: wait for the agent runtime to shutdown
// TODO: replace with Client
var builder = WebApplication.CreateBuilder();
//var app = await AgentsApp.PublishMessageAsync("HelloAgents", new NewMessageReceived
//{
//    Message = "World"
//}, local: true);
////var app = await AgentsApp.StartAsync();
var app = builder.Build();
await app.WaitForShutdownAsync();

namespace HelloAgent
{

    [TopicSubscription("HelloAgents")]
    public class HelloAgent( IHostApplicationLifetime hostApplicationLifetime,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : Agent(
        typeRegistry),
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>,
        IHandle<Shutdown>
    {
        public async Task Handle(NewMessageReceived item, CancellationToken cancellationToken = default)
        {
            var response = await SayHello(item.Message).ConfigureAwait(false);
            var evt = new Output { Message = response };
            await PublishEventAsync(evt).ConfigureAwait(false);
            var goodbye = new ConversationClosed
            {
                UserId = AgentId.Key,
                UserMessage = "Goodbye"
            };
            await PublishEventAsync(goodbye).ConfigureAwait(false);
        }
        public async Task Handle(ConversationClosed item, CancellationToken cancellationToken = default)
        {
            var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output { Message = goodbye };
            await PublishEventAsync(evt).ConfigureAwait(true);
            await PublishEventAsync(new Shutdown()).ConfigureAwait(false);
        }

        public async Task Handle(Shutdown item, CancellationToken cancellationToken = default)
        {
            Console.WriteLine("Shutting down...");
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
}
