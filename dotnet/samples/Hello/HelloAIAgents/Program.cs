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
var agentTypes = new AgentTypes(new Dictionary<string, Type>
{
    { "HelloAIAgents", typeof(HelloAIAgent) }
});
var app = await AgentsApp.PublishMessageAsync("HelloAgents", new NewMessageReceived
{
    Message = "World"
}, builder, agentTypes, local: true);

await app.WaitForShutdownAsync();

namespace Hello
{
    [TopicSubscription("agents")]
    public class HelloAgent(
        IAgentWorker worker,
        [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
        IHostApplicationLifetime hostApplicationLifetime) : ConsoleAgent(
            worker,
            typeRegistry),
            ISayHello,
            IHandle<NewMessageReceived>,
            IHandle<ConversationClosed>
    {
        public async Task Handle(NewMessageReceived item)
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
        public async Task Handle(ConversationClosed item)
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
