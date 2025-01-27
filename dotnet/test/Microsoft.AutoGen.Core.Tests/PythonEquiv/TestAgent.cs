// Copyright (c) Microsoft Corporation. All rights reserved.
// TestAgent.cs

using Microsoft.AutoGen.Contracts.Python;
using Microsoft.AutoGen.Core.Python;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.Core.Tests.Python;

public class TextMessage
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
        Core.Python.IHandle<TextMessage>,
        Core.Python.IHandle<string>,
        Core.Python.IHandle<int>
{
    public Task Handle(TextMessage item, MessageContext messageContext)
    {
        ReceivedMessages[item.Source] = item.Content;
        return Task.CompletedTask;
    }

    public Task Handle(string item, MessageContext messageContext)
    {
        ReceivedItems.Add(item);
        return Task.CompletedTask;
    }

    public Task Handle(int item, MessageContext messageContext)
    {
        ReceivedItems.Add(item);
        return Task.CompletedTask;
    }

    public List<object> ReceivedItems { get; private set; } = [];

    /// <summary>
    /// Key: source
    /// Value: message
    /// </summary>
    public static Dictionary<string, object> ReceivedMessages { get; private set; } = new();
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
