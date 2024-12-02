// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using System.Text.Json;
using Hello.Events;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Core;

// send a message to the agent
// TODO: replace with Client
var builder = WebApplication.CreateBuilder();
//var app = await AgentsApp.PublishMessageAsync("HelloAgents", new NewMessageReceived
//{
//    Message = "World"
//}, local: false);
var app = builder.Build();
await app.WaitForShutdownAsync();

namespace HelloAgentState
{

    [TopicSubscription("HelloAgents")]
    public class HelloAgent(
    IHostApplicationLifetime hostApplicationLifetime,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : Agent(
        typeRegistry),
        IHandle<NewMessageReceived>,
        IHandle<ConversationClosed>,
        IHandle<Shutdown>
    {
        private AgentState? State { get; set; }
        public async Task Handle(NewMessageReceived item, CancellationToken cancellationToken = default)
        {
            var response = await SayHello(item.Message).ConfigureAwait(false);
            var evt = new Output
            {
                Message = response
            };
            Dictionary<string, string> state = new()
        {
            { "data", "We said hello to " + item.Message },
            { "workflow", "Active" }
        };
            await StoreAsync(new AgentState
            {
                AgentId = AgentId,
                TextData = JsonSerializer.Serialize(state)
            }).ConfigureAwait(false);
            await PublishEventAsync(evt).ConfigureAwait(false);
            var goodbye = new ConversationClosed
            {
                UserId = AgentId.Key,
                UserMessage = "Goodbye"
            };
            await PublishEventAsync(goodbye).ConfigureAwait(false);
            // send the shutdown message
            await PublishEventAsync(new Shutdown { Message = AgentId.Key }).ConfigureAwait(false);

        }
        public async Task Handle(ConversationClosed item, CancellationToken cancellationToken = default)
        {
            State = await ReadAsync<AgentState>(AgentId).ConfigureAwait(false);
            var state = JsonSerializer.Deserialize<Dictionary<string, string>>(State.TextData) ?? new Dictionary<string, string> { { "data", "No state data found" } };
            var goodbye = $"\nState: {state}\n*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output
            {
                Message = goodbye
            };
            await PublishEventAsync(evt).ConfigureAwait(true);
            state["workflow"] = "Complete";
            await StoreAsync(new AgentState
            {
                AgentId = AgentId,
                TextData = JsonSerializer.Serialize(state)
            }).ConfigureAwait(false);
        }
        public async Task Handle(Shutdown item, CancellationToken cancellationToken = default)
        {
            string? workflow = null;
            // make sure the workflow is finished
            while (workflow != "Complete")
            {
                State = await ReadAsync<AgentState>(AgentId).ConfigureAwait(true);
                var state = JsonSerializer.Deserialize<Dictionary<string, string>>(State?.TextData ?? "{}") ?? new Dictionary<string, string>();
                workflow = state["workflow"];
                await Task.Delay(1000).ConfigureAwait(true);
            }
            // now we can shut down...
            hostApplicationLifetime.StopApplication();
        }
        public async Task<string> SayHello(string ask)
        {
            var response = $"\n\n\n\n***************Hello {ask}**********************\n\n\n\n";
            return response;
        }
    }
}
