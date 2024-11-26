// Copyright (c) Microsoft Corporation. All rights reserved.
// OutputAgent.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Backend.Agents;

[TopicSubscription("HelloAgents")]
public class OutputAgent(
        IAgentRuntime context,
        [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<OutputAgent> logger) : AgentBase(
            context,
            typeRegistry, logger),
            IHandle<NewGreetingGenerated>
{
    public async Task Handle(NewGreetingGenerated item)
    {
        _logger.LogInformation($"OutputAgent with Id: {AgentId} received NewGreetingGenerated with {item.UserMessage}");
    }
}
