// Copyright (c) Microsoft Corporation. All rights reserved.
// TestAgents.cs

using System.Text.Json;
using Microsoft.AutoGen.Contracts;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core.Tests;

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
    protected Dictionary<string, object> _receivedMessages = new();
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

[TypeSubscription("TestTopic")]
public class SubscribedSaveLoadAgent : TestAgent, ISaveState
{
    public SubscribedSaveLoadAgent(AgentId id,
        IAgentRuntime runtime,
        Logger<BaseAgent>? logger = null) : base(id, runtime, logger)
    {
    }

    ValueTask<JsonElement> ISaveState.SaveStateAsync()
    {
        var jsonDoc = JsonSerializer.SerializeToElement(_receivedMessages);
        return ValueTask.FromResult(jsonDoc);
    }

    ValueTask ISaveState.LoadStateAsync(JsonElement state)
    {
        _receivedMessages = JsonSerializer.Deserialize<Dictionary<string, object>>(state) ?? throw new InvalidOperationException("Failed to deserialize state");
        return ValueTask.CompletedTask;
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

public sealed class ReceiverAgent : BaseAgent, IHandle<BasicMessage>
{
    public List<BasicMessage> Messages { get; } = new();

    public ReceiverAgent(AgentId id, IAgentRuntime runtime, string description, ILogger<BaseAgent>? logger = null)
        : base(id, runtime, description, logger)
    {
    }

    public bool DidReceive => this.Messages.Count > 0;

    public ValueTask HandleAsync(BasicMessage item, MessageContext messageContext)
    {
        this.Messages.Add(item);

        return ValueTask.CompletedTask;
    }
}

public sealed class ProcessorAgent : BaseAgent, IHandle<BasicMessage, BasicMessage>
{
    private Func<string, string> ProcessFunc { get; }

    public ProcessorAgent(AgentId id, IAgentRuntime runtime, Func<string, string> processFunc, string description, ILogger<BaseAgent>? logger = null)
        : base(id, runtime, description, logger)
    {
        this.ProcessFunc = processFunc;
    }

    public bool DidProcess => this.ProcessedMessage != null;
    public BasicMessage? ProcessedMessage { get; private set; }

    public ValueTask<BasicMessage> HandleAsync(BasicMessage item, MessageContext messageContext)
    {
        this.ProcessedMessage = item;
        BasicMessage result = new() { Content = this.ProcessFunc(item.Content) };

        return ValueTask.FromResult(result);
    }
}

public sealed class CancelAgent : BaseAgent, IHandle<BasicMessage, BasicMessage>
{
    public CancelAgent(AgentId id, IAgentRuntime runtime, string description, ILogger<BaseAgent>? logger = null)
        : base(id, runtime, description, logger)
    {
    }

    public bool DidCancel { get; private set; }

    public ValueTask<BasicMessage> HandleAsync(BasicMessage item, MessageContext messageContext)
    {
        this.DidCancel = true;

        CancellationToken cancelledToken = new CancellationToken(canceled: true);
        cancelledToken.ThrowIfCancellationRequested();

        return ValueTask.FromResult(item);
    }
}

public sealed class TestException : Exception
{ }

public sealed class ErrorAgent : BaseAgent, IHandle<BasicMessage, BasicMessage>
{
    public ErrorAgent(AgentId id, IAgentRuntime runtime, string description, ILogger<BaseAgent>? logger = null)
        : base(id, runtime, description, logger)
    {
    }

    public bool DidThrow { get; private set; }

    public ValueTask<BasicMessage> HandleAsync(BasicMessage item, MessageContext messageContext)
    {
        this.DidThrow = true;

        throw new TestException();
    }
}
