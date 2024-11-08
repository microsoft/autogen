// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

// step 1: create in-memory agent runtime

// step 2: register HelloAgent to that agent runtime

// step 3: start the agent runtime

// step 4: send a message to the agent

// step 5: wait for the agent runtime to shutdown
var app = await AgentsApp.PublishMessageAsync("HelloAgents", new NewMessageReceived
{
    Message = "World"
}, local: false);

await app.WaitForShutdownAsync();

namespace Hello
{
    [TopicSubscription("HelloAgents")]
    public class HelloAgent(
        IAgentContext context,
        [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
        IHostApplicationLifetime hostApplicationLifetime) : AgentBase(
            context,
            typeRegistry),
            ISayHello,
            IHandleConsole,
            IHandle<NewMessageReceived>,
            IHandle<ConversationClosed>
    {
        public async Task Handle(NewMessageReceived item)
        {
            var response = await SayHello(item.Message).ConfigureAwait(false);
            var evt = new Output { Message = response };
            await PublishMessageAsync(evt).ConfigureAwait(false);
            var goodbye = new ConversationClosed
            {
                UserId = this.AgentId.Key,
                UserMessage = "Goodbye"
            };
            await PublishMessageAsync(goodbye).ConfigureAwait(false);
        }
        public async Task Handle(ConversationClosed item)
        {
            var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output
            {
                Message = goodbye
            };
            await PublishMessageAsync(evt).ConfigureAwait(false);

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
}
