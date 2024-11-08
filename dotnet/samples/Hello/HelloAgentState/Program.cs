// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

// send a message to the agent
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
        [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : ConsoleAgent(
            context,
            typeRegistry),
            ISayHello,
            IHandle<NewMessageReceived>,
            IHandle<ConversationClosed>
    {
        private AgentState? State { get; set; }
        public async Task Handle(NewMessageReceived item)
        {
            var response = await SayHello(item.Message).ConfigureAwait(false);
            var evt = new Output
            {
                Message = response
            };
            var entry = "We said hello to " + item.Message;
            await Store(new AgentState
            {
                AgentId = this.AgentId,
                TextData = entry
            }).ConfigureAwait(false);
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
            State = await Read<AgentState>(this.AgentId).ConfigureAwait(false);
            var read = State?.TextData ?? "No state data found";
            var goodbye = $"{read}\n*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output
            {
                Message = goodbye
            };
            await PublishMessageAsync(evt).ConfigureAwait(false);
            //sleep
            await Task.Delay(10000).ConfigureAwait(false);
            await AgentsApp.ShutdownAsync().ConfigureAwait(false);

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
