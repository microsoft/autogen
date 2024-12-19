// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Hello.Events;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

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
    [FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry, ILogger<HelloAgent> logger) : Agent(
        typeRegistry, logger),
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>,
        IHandle<Shutdown>
    {
        public async Task Handle(NewMessageReceived item, CancellationToken cancellationToken = default)
        {
            logger.LogInformation($"New message received on Agent with ID:{AgentId.Key}");
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
            logger.LogInformation($"Conversation closed on Agent with ID:{AgentId.Key} with message {goodbye}");
            var evt = new Output { Message = goodbye };
            await PublishEventAsync(evt).ConfigureAwait(true);
            if (Environment.GetEnvironmentVariable("STAY_ALIVE_ON_GOODBYE") != "true")
            {
                await PublishEventAsync(new Shutdown()).ConfigureAwait(false);
            }
        }

        public async Task Handle(Shutdown item, CancellationToken cancellationToken = default)
        {
            logger.LogInformation("Shutting down...");
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
