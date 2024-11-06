// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

// send a message to the agent
var app = await AgentsApp.PublishMessageAsync("HelloAgents", new NewMessageReceived
{
    Message = "World"
}, local: true);

await app.WaitForShutdownAsync();

namespace Hello
{
    [TopicSubscription("HelloAgents")]
    public class HelloAgent(
        IAgentRuntime context,
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
            }.ToCloudEvent(this.AgentId.Key);
            var entry = "We said hello to " + item.Message;
            await StoreAsync(new AgentState
            {
                AgentId = this.AgentId,
                TextData = entry
            }).ConfigureAwait(false);
            await PublishEventAsync(evt).ConfigureAwait(false);
            var goodbye = new ConversationClosed
            {
                UserId = this.AgentId.Key,
                UserMessage = "Goodbye"
            }.ToCloudEvent(this.AgentId.Key);
            await PublishEventAsync(goodbye).ConfigureAwait(false);
        }
        public async Task Handle(ConversationClosed item)
        {
            State = await ReadAsync<AgentState>(this.AgentId).ConfigureAwait(false);
            var read = State?.TextData ?? "No state data found";
            var goodbye = $"{read}\n*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output
            {
                Message = goodbye
            }.ToCloudEvent(this.AgentId.Key);
            await PublishEventAsync(evt).ConfigureAwait(false);
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
