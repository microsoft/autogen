// Copyright (c) Microsoft Corporation. All rights reserved.
// HelloAIAgent.cs

using Hello;
using Hello.Events;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.AI;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace HelloAIAgents;
[TopicSubscription("HelloAgents")]
public class HelloAIAgent(
    [FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry,
    IChatClient client, ILogger<HelloAIAgent> logger) : HelloAgent(typeRegistry, logger),
        IHandle<NewMessageReceived>
{
    public async Task Handle(NewMessageReceived item, CancellationToken cancellationToken)
    {
        var prompt = "Please write a limerick greeting someone with the name " + item.Message;
        var response = await client.CompleteAsync(prompt);
        logger.LogInformation($"Response from AI: {response.Message.Text}");
        var evt = new Output { Message = response.Message.Text };
        await PublishEventAsync(evt).ConfigureAwait(false);

        var goodbye = new ConversationClosed { UserId = AgentId.Key, UserMessage = "Goodbye" };
        await PublishEventAsync(goodbye).ConfigureAwait(false);
    }
}
