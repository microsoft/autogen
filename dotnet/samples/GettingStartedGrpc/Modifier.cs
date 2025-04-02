// Copyright (c) Microsoft Corporation. All rights reserved.
// Modifier.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;

using ModifyF = System.Func<int, int>;

namespace GettingStartedGrpcSample;

[TypeSubscription("default")]
public class Modifier(
    AgentId id,
    IAgentRuntime runtime,
    ModifyF modifyFunc
    ) :
        BaseAgent(id, runtime, "Modifier", null),
        IHandle<Events.CountMessage>
{

    public async ValueTask HandleAsync(Events.CountMessage item, MessageContext messageContext)
    {
        int newValue = modifyFunc(item.Content);
        Console.WriteLine($"\nModifier:\nModified {item.Content} to {newValue}");

        var updateMessage = new Events.CountUpdate { NewCount = newValue };
        await this.PublishMessageAsync(updateMessage, topic: new TopicId("default"));
    }
}
