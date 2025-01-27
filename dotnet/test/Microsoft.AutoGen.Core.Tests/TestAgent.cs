// Copyright (c) Microsoft Corporation. All rights reserved.
// TestAgent.cs

using System.Collections.Concurrent;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
namespace Microsoft.AutoGen.Core.Tests;
/// <summary>
/// The test agent is a simple agent that is used for testing purposes.
/// </summary>
public class TestAgent(
    [FromKeyedServices("AgentsMetadata")] AgentsMetadata eventTypes,
    Logger<Agent>? logger = null) : Agent(eventTypes, logger), IHandle<TextMessage>
{
    public Task Handle(TextMessage item, CancellationToken cancellationToken = default)
    {
        ReceivedMessages[item.Source] = item.TextMessage_;
        return Task.CompletedTask;
    }
    public Task Handle(string item)
    {
        ReceivedItems.Add(item);
        return Task.CompletedTask;
    }
    public Task Handle(int item)
    {
        ReceivedItems.Add(item);
        return Task.CompletedTask;
    }
    public List<object> ReceivedItems { get; private set; } = [];

    /// <summary>
    /// Key: source
    /// Value: message
    /// </summary>
    public static ConcurrentDictionary<string, object> ReceivedMessages { get; private set; } = new();
}
