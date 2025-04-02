// Copyright (c) Microsoft Corporation. All rights reserved.
// TestAgent.cs
using System.Collections.Concurrent;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;
using Microsoft.AutoGen.Protobuf;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests;

[TypeSubscription("gh-gh-gh")]
public class PBAgent(Contracts.AgentId id, IAgentRuntime runtime, ILogger<BaseAgent>? logger = null)
    : BaseAgent(id, runtime, "Test Agent", logger),
    IHandle<NewMessageReceived>,
    IHandle<GoodBye>
{
    public async ValueTask HandleAsync(NewMessageReceived item, MessageContext messageContext)
    {
        var key = messageContext.MessageId ?? Guid.NewGuid().ToString();
        ReceivedMessages.AddOrUpdate(key, item.Message, (k, v) => item.Message);
        var hello = new Hello { Message = item.Message };
        var typeFullName = typeof(Hello).FullName ?? throw new InvalidOperationException("Type full name is null");
        await PublishMessageAsync(hello, new TopicId(typeFullName), "gh-gh-gh");
    }
    public async ValueTask HandleAsync(GoodBye item, MessageContext context)
    {
        _logger.LogInformation($"Received GoodBye message {item.Message}");
    }
    public static ConcurrentDictionary<string, object> ReceivedMessages { get; private set; } = new();
}

[TypeSubscription("gh-gh-gh")]
public class GMAgent(Contracts.AgentId id, IAgentRuntime runtime, ILogger<BaseAgent>? logger = null)
    : BaseAgent(id, runtime, "Test Agent", logger),
    IHandle<Hello>
{
    public async ValueTask HandleAsync(Hello item, MessageContext messageContext)
    {
        var key = messageContext.MessageId ?? Guid.NewGuid().ToString();
        ReceivedMessages.AddOrUpdate(key, item.Message, (k, v) => item.Message);
        var typeFullName = typeof(GoodBye).FullName ?? throw new InvalidOperationException("Type full name is null");
        await PublishMessageAsync(new GoodBye { Message = "" }, new TopicId(typeFullName, "gh-gh-gh"));
    }
    public static ConcurrentDictionary<string, object> ReceivedMessages { get; private set; } = new();
}
