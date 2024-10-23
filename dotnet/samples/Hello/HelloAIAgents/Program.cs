using Hello;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

// send a message to the agent
var builder = WebApplication.CreateBuilder();
// put these in your environment or appsettings.json
builder.Configuration["HelloAIAgents:ModelType"] = "azureopenai";
builder.Configuration["HelloAIAgents:LlmModelName"] = "gpt-3.5-turbo";
Environment.SetEnvironmentVariable("AZURE_OPENAI_CONNECTION_STRING", "Endpoint=https://TODO.openai.azure.com/;Key=TODO;Deployment=TODO");
if (Environment.GetEnvironmentVariable("AZURE_OPENAI_CONNECTION_STRING") == null)
{
    throw new InvalidOperationException("AZURE_OPENAI_CONNECTION_STRING not set, try something like AZURE_OPENAI_CONNECTION_STRING = \"Endpoint=https://TODO.openai.azure.com/;Key=TODO;Deployment=TODO\"");
}
builder.Configuration["ConectionStrings:HelloAIAgents"] = Environment.GetEnvironmentVariable("AZURE_OPENAI_CONNECTION_STRING");
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
        public async Task Handle(NewMessageReceived item)
        {
            var response = await SayHello(item.Message).ConfigureAwait(false);
            var evt = new Output
            {
                Message = response
            }.ToCloudEvent(this.AgentId.Key);
            await PublishEvent(evt).ConfigureAwait(false);
            var goodbye = new ConversationClosed
            {
                UserId = this.AgentId.Key,
                UserMessage = "Goodbye"
            }.ToCloudEvent(this.AgentId.Key);
            await PublishEvent(goodbye).ConfigureAwait(false);
        }
        public async Task Handle(ConversationClosed item)
        {
            var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
            var evt = new Output
            {
                Message = goodbye
            }.ToCloudEvent(this.AgentId.Key);
            await PublishEvent(evt).ConfigureAwait(false);
            //sleep30 seconds
            await Task.Delay(30000).ConfigureAwait(false);
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
