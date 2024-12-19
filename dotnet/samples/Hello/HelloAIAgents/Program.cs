// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Hello.Events;
using HelloAIAgents;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var agentTypes = new AgentTypes(new Dictionary<string, Type>
{
    { "HelloAIAgents", typeof(HelloAIAgent) }
});
var app = await AgentsApp.PublishMessageAsync("HelloAgents", new NewMessageReceived
{
    Message = "World"
},null, agentTypes, local: true, addChatClient: true);

await app.WaitForShutdownAsync();

namespace Hello
{
    [TopicSubscription("agents")]
    public class HelloAgent(
        [FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry, ILogger<HelloAgent> logger) : Agent(
        typeRegistry),
        IHandle<ConversationClosed>
    {
        public async Task Handle(ConversationClosed item, CancellationToken cancellationToken = default)
        {

            var goodbye = $"*********************  {item.UserId} said {item.UserMessage}  ************************";
            logger.LogInformation($"Conversation closed on Agent with ID:{AgentId.Key} with message {goodbye}");
            var evt = new Output
            {
                Message = goodbye
            };
            await PublishEventAsync(evt).ConfigureAwait(false);
        }
    }
}
