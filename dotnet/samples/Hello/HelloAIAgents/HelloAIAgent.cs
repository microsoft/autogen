// Copyright (c) Microsoft Corporation. All rights reserved.
// HelloAIAgent.cs

using Hello.Events;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.AI;

namespace HelloAIAgents;
[TopicSubscription("HelloAgents")]
public class HelloAIAgent(
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
    IHostApplicationLifetime hostApplicationLifetime,
    IChatClient client) : HelloAgent(
        typeRegistry,
        hostApplicationLifetime),
        IHandle<NewMessageReceived>
{
    // This Handle supercedes the one in the base class
    public async Task Handle(NewMessageReceived item)
    {
        var prompt = "Please write a limerick greeting someone with the name " + item.Message;
        var response = await client.CompleteAsync(prompt);
        var evt = new Output { Message = response.Message.Text };
        await PublishEventAsync(evt).ConfigureAwait(false);

        var goodbye = new ConversationClosed { UserId = AgentId.Key, UserMessage = "Goodbye" };
        await PublishEventAsync(goodbye).ConfigureAwait(false);
    }
}
