// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using System.Text.Json;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;

// send a message to the agent
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
            IHandleConsole,
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
                AgentId = this.AgentId,
                TextData = JsonSerializer.Serialize(state)
            }).ConfigureAwait(false);
            await PublishMessageAsync(evt).ConfigureAwait(false);
            var goodbye = new ConversationClosed
            {
                UserId = this.AgentId.Key,
                UserMessage = "Goodbye"
            };
            await PublishMessageAsync(goodbye).ConfigureAwait(false);
            // send the shutdown message
            await PublishMessageAsync(new Shutdown { Message = this.AgentId.Key }).ConfigureAwait(false);

        }
        public async Task Handle(ConversationClosed item, CancellationToken cancellationToken = default)
        {
            State = await ReadAsync<AgentState>(this.AgentId).ConfigureAwait(false);
            var state = JsonSerializer.Deserialize<Dictionary<string, string>>(State.TextData) ?? new Dictionary<string, string> { { "data", "No state data found" } };
            var goodbye = $"\nState: {state}\n*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output
            {
                Message = goodbye
            };
            await PublishMessageAsync(evt).ConfigureAwait(true);
            state["workflow"] = "Complete";
            await StoreAsync(new AgentState
            {
                AgentId = this.AgentId,
                TextData = JsonSerializer.Serialize(state)
            }).ConfigureAwait(false);
        }
        public async Task Handle(Shutdown item, CancellationToken cancellationToken = default)
        {
            string? workflow = null;
            // make sure the workflow is finished
            while (workflow != "Complete")
            {
                State = await ReadAsync<AgentState>(this.AgentId).ConfigureAwait(true);
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
