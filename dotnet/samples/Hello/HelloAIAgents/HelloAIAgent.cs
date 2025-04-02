// Copyright (c) Microsoft Corporation. All rights reserved.
// HelloAIAgent.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.AI;

namespace Hello;
[TopicSubscription("agents")]
public class HelloAIAgent(
    [FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry,
    IHostApplicationLifetime hostApplicationLifetime,
    IChatClient client) : HelloAgent(
        typeRegistry,
        hostApplicationLifetime),
        IHandle<NewMessageReceived>
{
    // This Handle supercedes the one in the base class
    public new async Task Handle(NewMessageReceived item, CancellationToken cancellationToken = default)
    {
        var prompt = "Please write a limerick greeting someone with the name " + item.Message;
        var response = await client.CompleteAsync(prompt);
        var evt = new Output { Message = response.Message.Text };
        await PublishMessageAsync(evt).ConfigureAwait(false);

        var goodbye = new ConversationClosed { UserId = this.AgentId.Key, UserMessage = "Goodbye" };
        await PublishMessageAsync(goodbye).ConfigureAwait(false);
    }
}
