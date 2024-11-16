// Copyright (c) Microsoft Corporation. All rights reserved.
// OutputAgent.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Backend.Agents;

[TopicSubscription("HelloAgents")]
public class OutputAgent(
        IAgentRuntime context,
        [FromKeyedServices("EventTypes")] EventTypes typeRegistry) : AgentBase(
            context,
            typeRegistry),
            IHandleConsole,
            IHandle<NewGreetingGenerated>
{
    public async Task Handle(NewGreetingGenerated item)
    {
        // TODO: store to memory
       
    }
}
