// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var local = true;
if (Environment.GetEnvironmentVariable("AGENT_HOST") != null) { local = false; }
var app = await Microsoft.AutoGen.Core.Grpc.AgentsApp.PublishMessageAsync("HelloAgents", new NewMessageReceived
{
    Message = "World"
}, local: local).ConfigureAwait(false);
await app.WaitForShutdownAsync();

namespace Hello
{
    [TopicSubscription("HelloAgents")]
    public class HelloAgent(
        IHostApplicationLifetime hostApplicationLifetime,
        [FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry) : Agent(
            typeRegistry),
            ISayHello,
            IHandleConsole,
            IHandle<NewMessageReceived>,
            IHandle<ConversationClosed>,
            IHandle<Shutdown>
    {
        public async Task Handle(NewMessageReceived item, CancellationToken cancellationToken)
        {
            var response = await SayHello(item.Message).ConfigureAwait(false);
            var evt = new Output { Message = response };
            await PublishMessageAsync(evt).ConfigureAwait(false);
            var goodbye = new ConversationClosed
            {
                UserId = this.AgentId.Type,
                UserMessage = "Goodbye"
            };
            await PublishMessageAsync(goodbye).ConfigureAwait(false);
        }
        public async Task Handle(ConversationClosed item, CancellationToken cancellationToken)
        {
            var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output { Message = goodbye };
            await PublishMessageAsync(evt).ConfigureAwait(true);
            if (Environment.GetEnvironmentVariable("STAY_ALIVE_ON_GOODBYE") != "true")
            {
                await PublishMessageAsync(new Shutdown()).ConfigureAwait(false);
            }
        }

        public async Task Handle(Shutdown item, CancellationToken cancellationToken)
        {
            Console.WriteLine("Shutting down...");
            hostApplicationLifetime.StopApplication();
        }

        public async Task<string> SayHello(string ask, CancellationToken cancellationToken = default)
        {
            var response = $"\n\n\n\n***************Hello {ask}**********************\n\n\n\n";
            return response;
        }
    }
    public interface ISayHello
    {
        public Task<string> SayHello(string ask, CancellationToken cancellationToken = default);
    }
}
