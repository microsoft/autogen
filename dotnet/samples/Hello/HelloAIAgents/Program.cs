// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Hello;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;

// send a message to the agent
var builder = new HostApplicationBuilder();
// put these in your environment or appsettings.json
builder.Configuration["HelloAIAgents:ModelType"] = "azureopenai";
builder.Configuration["HelloAIAgents:LlmModelName"] = "gpt-3.5-turbo";
Environment.SetEnvironmentVariable("AZURE_OPENAI_CONNECTION_STRING", "Endpoint=https://TODO.openai.azure.com/;Key=TODO;Deployment=TODO");
if (Environment.GetEnvironmentVariable("AZURE_OPENAI_CONNECTION_STRING") == null)
{
    throw new InvalidOperationException("AZURE_OPENAI_CONNECTION_STRING not set, try something like AZURE_OPENAI_CONNECTION_STRING = \"Endpoint=https://TODO.openai.azure.com/;Key=TODO;Deployment=TODO\"");
}
builder.Configuration["ConnectionStrings:HelloAIAgents"] = Environment.GetEnvironmentVariable("AZURE_OPENAI_CONNECTION_STRING");
builder.AddChatCompletionService("HelloAIAgents");
var _ = new AgentTypes(new Dictionary<string, Type>
{
    { "HelloAIAgents", typeof(HelloAIAgent) }
});
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
        [FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry,
        IHostApplicationLifetime hostApplicationLifetime) : ConsoleAgent(
            typeRegistry),
            ISayHello,
            IHandle<NewMessageReceived>,
            IHandle<ConversationClosed>
    {
        public async Task Handle(NewMessageReceived item, CancellationToken cancellationToken = default)
        {
            var response = await SayHello(item.Message).ConfigureAwait(false);
            var evt = new Output
            {
                Message = response
            };
            await PublishMessageAsync(evt).ConfigureAwait(false);
            var goodbye = new ConversationClosed
            {
                UserId = this.AgentId.Key,
                UserMessage = "Goodbye"
            };
            await PublishMessageAsync(goodbye).ConfigureAwait(false);
        }
        public async Task Handle(ConversationClosed item, CancellationToken cancellationToken = default)
        {
            var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output
            {
                Message = goodbye
            };
            await PublishMessageAsync(evt).ConfigureAwait(false);
            //sleep30 seconds
            await Task.Delay(30000).ConfigureAwait(false);
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
