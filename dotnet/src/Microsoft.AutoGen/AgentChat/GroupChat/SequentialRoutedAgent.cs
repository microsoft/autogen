// Copyright (c) Microsoft Corporation. All rights reserved.
// SequentialRoutedAgent.cs

// TODO: Inconsistency viz Python
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public class SequentialRoutedAgent : AgentBase
{
    // TODO: Where does this instantiation come in?
    public SequentialRoutedAgent(IAgentRuntime context, EventTypes eventTypes) : base(context, eventTypes)
    {
    }

    public override Task HandleObject(object item)
    {
        return base.HandleObject(item);
    }

    protected async ValueTask PublishMessageAsync(object message, string topicId)
    {
        throw new NotImplementedException();
    }
}
