// Copyright (c) Microsoft Corporation. All rights reserved.
// TestProtobufAgent.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core.Grpc.Tests.Protobuf;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core.Grpc.Tests;

/// <summary>
/// The test agent is a simple agent that is used for testing purposes.
/// </summary>
public class TestProtobufAgent(AgentId id,
        IAgentRuntime runtime,
        Logger<BaseAgent>? logger = null) : BaseAgent(id, runtime, "Test Agent", logger),
        IHandle<TextMessage>,
        IHandle<RpcTextMessage, RpcTextMessage>

{
    public ValueTask HandleAsync(TextMessage item, MessageContext messageContext)
    {
        ReceivedMessages[item.Source] = item.Content;
        return ValueTask.CompletedTask;
    }

    public ValueTask<RpcTextMessage> HandleAsync(RpcTextMessage item, MessageContext messageContext)
    {
        ReceivedMessages[item.Source] = item.Content;
        return ValueTask.FromResult(new RpcTextMessage { Source = item.Source, Content = item.Content });
    }

    public List<object> ReceivedItems { get; private set; } = [];

    /// <summary>
    /// Key: source
    /// Value: message
    /// </summary>
    private readonly Dictionary<string, object> _receivedMessages = new();
    public Dictionary<string, object> ReceivedMessages => _receivedMessages;
}

[TypeSubscription("TestTopic")]
public class SubscribedProtobufAgent : TestProtobufAgent
{
    public SubscribedProtobufAgent(AgentId id,
        IAgentRuntime runtime,
        Logger<BaseAgent>? logger = null) : base(id, runtime, logger)
    {
    }
}
