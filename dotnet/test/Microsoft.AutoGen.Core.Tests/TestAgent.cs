// Copyright (c) Microsoft Corporation. All rights reserved.
// TestAgent.cs

using System.Collections.Concurrent;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Tests.Events;

namespace Microsoft.AutoGen.Core.Tests;

[TopicSubscription("default")]
public class TestAgent([FromKeyedServices("AgentsMetadata")] AgentsMetadata eventTypes, ILogger<Agent>? logger = null)
    : Agent(eventTypes, logger)
    , IHandle<GoodBye>
    , IHandle<TextMessage>
{
    public Task Handle(GoodBye item, CancellationToken cancellationToken)
    {
        _logger.LogInformation($"Received GoodBye message {item.Message}");
        return Task.CompletedTask;
    }

    public Task Handle(TextMessage item, CancellationToken cancellationToken = default)
    {
        ReceivedMessages[item.Source] = item.Message;
        return Task.CompletedTask;
    }

    public static ConcurrentDictionary<string, object> ReceivedMessages { get; private set; } = new();
}
