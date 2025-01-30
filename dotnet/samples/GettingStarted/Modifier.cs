// Copyright (c) Microsoft Corporation. All rights reserved.
// Modifier.cs
#region snippet_Modifier
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;

using ModifyF = System.Func<int, int>;

namespace GettingStartedSample;

[TypeSubscription("default")]
public class Modifier(
    AgentId id,
    IAgentRuntime runtime,
    ModifyF modifyFunc
    ) :
        BaseAgent(id, runtime, "Modifier", null),
        IHandle<CountMessage>
{

    public async ValueTask HandleAsync(CountMessage item, MessageContext messageContext)
    {
        int newValue = modifyFunc(item.Content);
        Console.WriteLine($"\nModifier:\nModified {item.Content} to {newValue}");

        CountUpdate updateMessage = new CountUpdate { NewCount = newValue };
        await this.PublishMessageAsync(updateMessage, topic: new TopicId("default"));
    }
}
#endregion snippet_Modifier
