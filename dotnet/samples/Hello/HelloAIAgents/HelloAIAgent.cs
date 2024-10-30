// Copyright (c) Microsoft Corporation. All rights reserved.
// HelloAIAgent.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.Extensions.AI;
using Microsoft.Extensions.DependencyInjection;

namespace Hello;
[TopicSubscription("HelloAgents")]
public class HelloAIAgent(
    IAgentContext context,
    [FromKeyedServices("EventTypes")] EventTypes typeRegistry,
    IChatClient client) : HelloAgent(
        context,
        typeRegistry),
        IHandle<NewMessageReceived>
{
    // This Handle supercedes the one in the base class
    public new async Task Handle(NewMessageReceived item)
    {
        var prompt = "Please write a limerick greeting someone with the name " + item.Message;
        var response = await client.CompleteAsync(prompt);
        var evt = new Output
        {
            Message = response.Message.Text
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(evt).ConfigureAwait(false);
        var goodbye = new ConversationClosed
        {
            UserId = this.AgentId.Key,
            UserMessage = "Goodbye"
        }.ToCloudEvent(this.AgentId.Key);
        await PublishEvent(goodbye).ConfigureAwait(false);
    }
}
