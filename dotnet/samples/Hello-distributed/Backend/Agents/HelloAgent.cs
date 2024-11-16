// Copyright (c) Microsoft Corporation. All rights reserved.
// HelloAgent.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Backend.Agents;

[TopicSubscription("HelloAgents")]
public class HelloAgent(
        IAgentRuntime context,
        [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : AgentBase(
            context,
            typeRegistry),
            IHandleConsole,
            IHandle<NewGreetingRequested>
{
    public async Task Handle(NewGreetingRequested item)
    {
        var response = await SayHello(item.Message).ConfigureAwait(false);
        var evt = new Output { Message = response };
        await PublishMessageAsync(evt).ConfigureAwait(false);
        var goodbye = new NewGreetingGenerated
        {
            UserId = AgentId.Key,
            UserMessage = "Goodbye"
        };
        await PublishMessageAsync(goodbye).ConfigureAwait(false);
    }

    public async Task<string> SayHello(string ask)
    {
        var response = $"\n\n\n\n***************Hello {ask}**********************\n\n\n\n";
        return response;
    }
}
