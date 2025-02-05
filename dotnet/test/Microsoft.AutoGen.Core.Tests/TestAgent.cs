// Copyright (c) Microsoft Corporation. All rights reserved.
// TestAgent.cs

using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core.Tests;

public class TextMessage
{
    public string Source { get; set; } = "";
    public string Content { get; set; } = "";
}

public class RpcTextMessage
{
    public string Source { get; set; } = "";
    public string Content { get; set; } = "";
}

/// <summary>
/// The test agent is a simple agent that is used for testing purposes.
/// </summary>
public class TestAgent(AgentId id,
        IAgentRuntime runtime,
        Logger<BaseAgent>? logger = null) : BaseAgent(id, runtime, "Test Agent", logger),
        IHandle<TextMessage>,
        IHandle<string>,
        IHandle<RpcTextMessage, string>

{
    public ValueTask HandleAsync(TextMessage item, MessageContext messageContext)
    {
        ReceivedMessages[item.Source] = item.Content;
        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(string item, MessageContext messageContext)
    {
        ReceivedItems.Add(item);
        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(int item, MessageContext messageContext)
    {
        ReceivedItems.Add(item);
        return ValueTask.CompletedTask;
    }

    public ValueTask<string> HandleAsync(RpcTextMessage item, MessageContext messageContext)
    {
        ReceivedMessages[item.Source] = item.Content;
        return ValueTask.FromResult(item.Content);
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
public class SubscribedAgent : TestAgent
{
    public SubscribedAgent(AgentId id,
        IAgentRuntime runtime,
        Logger<BaseAgent>? logger = null) : base(id, runtime, logger)
    {
    }
}

/// <summary>
/// The test agent showing an agent that subscribes to itself.
/// </summary>
[TypeSubscription("TestTopic")]
public class SubscribedSelfPublishAgent(AgentId id,
        IAgentRuntime runtime,
        Logger<BaseAgent>? logger = null) : BaseAgent(id, runtime, "Test Agent", logger),
        IHandle<string>,
        IHandle<TextMessage>
{
    public async ValueTask HandleAsync(string item, MessageContext messageContext)
    {
        TextMessage strToText = new TextMessage
        {
            Source = "TestTopic",
            Content = item
        };
        // This will publish the new message type which will be handled by the TextMessage handler
        await this.PublishMessageAsync(strToText, new TopicId("TestTopic"));
    }
    public ValueTask HandleAsync(TextMessage item, MessageContext messageContext)
    {
        _text = item;
        return ValueTask.CompletedTask;
    }

    private TextMessage _text = new TextMessage { Source = "DefaultTopic", Content = "DefaultContent" };
    public TextMessage Text => _text;
}
