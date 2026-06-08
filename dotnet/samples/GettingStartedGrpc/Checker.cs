// Copyright (c) Microsoft Corporation. All rights reserved.
// Checker.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.Hosting;
using TerminationF = System.Func<int, bool>;

namespace GettingStartedGrpcSample;

[TypeSubscription("default")]
public class Checker(
    AgentId id,
    IAgentRuntime runtime,
    IHostApplicationLifetime hostApplicationLifetime,
    TerminationF runUntilFunc
    ) :
        BaseAgent(id, runtime, "Modifier", null),
        IHandle<Events.CountUpdate>
{
    public async ValueTask HandleAsync(Events.CountUpdate item, MessageContext messageContext)
    {
        if (!runUntilFunc(item.NewCount))
        {
            Console.WriteLine($"\nChecker:\n{item.NewCount} passed the check, continue.");
            await this.PublishMessageAsync(new Events.CountMessage { Content = item.NewCount }, new TopicId("default"));
        }
        else
        {
            Console.WriteLine($"\nChecker:\n{item.NewCount} failed the check, stopping.");
            hostApplicationLifetime.StopApplication();
        }
    }
}
