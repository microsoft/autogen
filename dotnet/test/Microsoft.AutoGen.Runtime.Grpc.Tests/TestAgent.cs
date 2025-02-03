// Copyright (c) Microsoft Corporation. All rights reserved.
// TestAgent.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Runtime.Grpc.Tests;

[TopicSubscription("gh-gh-gh")]
public class PBAgent([FromKeyedServices("AgentsMetadata")] AgentsMetadata eventTypes, ILogger<Agent>? logger = null)
    : Agent(eventTypes, logger)
    , IHandle<NewMessageReceived>
    , IHandle<GoodBye>
{
    public async Task Handle(NewMessageReceived item, CancellationToken cancellationToken = default)
    {
        ReceivedMessages[AgentId.Key] = item.Message;
        var hello = new Hello { Message = item.Message };
        await PublishMessageAsync(hello);
    }
    public Task Handle(GoodBye item, CancellationToken cancellationToken)
    {
        _logger.LogInformation($"Received GoodBye message {item.Message}");
        return Task.CompletedTask;
    }

    public static ConcurrentDictionary<string, object> ReceivedMessages { get; private set; } = new();
}

[TopicSubscription("gh-gh-gh")]
public class GMAgent([FromKeyedServices("AgentsMetadata")] AgentsMetadata eventTypes, ILogger<Agent>? logger = null)
    : Agent(eventTypes, logger)
    , IHandle<Hello>
{
    public async Task Handle(Hello item, CancellationToken cancellationToken)
    {
        _logger.LogInformation($"Received Hello message {item.Message}");
        ReceivedMessages[AgentId.Key] = item.Message;
        await PublishMessageAsync(new GoodBye { Message = "" });
    }

    public static ConcurrentDictionary<string, object> ReceivedMessages { get; private set; } = new();
}
