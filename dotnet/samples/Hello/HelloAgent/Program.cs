// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Hello.Events;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var local = true;
if (Environment.GetEnvironmentVariable("AGENT_HOST") != null) { local = false; }
var app = await AgentsApp.PublishMessageAsync("HelloAgents", new NewMessageReceived
{
    Message = "World"
}, local: local).ConfigureAwait(false);
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
