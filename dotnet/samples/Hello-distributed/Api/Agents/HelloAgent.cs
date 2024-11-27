// Copyright (c) Microsoft Corporation. All rights reserved.
// HelloAgent.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Api.Agents;

[TopicSubscription("HelloAgents")]
public class HelloAgent(
        IAgentRuntime context,
        [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<HelloAgent> logger) : AgentBase(
            context,
            typeRegistry, logger),
            IHandle<NewGreetingRequested>
{
    public async Task Handle(NewGreetingRequested item)
    {
        _logger.LogInformation($"HelloAgent with Id: {AgentId} received NewGreetingRequested with {item.Message}");
        var response = await SayHello(item.Message).ConfigureAwait(false);
        var greeting = new NewGreetingGenerated
        {
            UserId = AgentId.Key,
            UserMessage = response
        };
        await PublishMessageAsync(greeting).ConfigureAwait(false);
    }

    public async Task<string> SayHello(string ask)
    {
        var response = $"\n\n\n\n***************Hello {ask}**********************\n\n\n\n";
        return response;
    }
}
