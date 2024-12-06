// Copyright (c) Microsoft Corporation. All rights reserved.
// SequentialRoutedAgent.cs

// TODO: Inconsistency viz Python
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public interface ITodoMakeProto
{
    public Google.Protobuf.IMessage ToProtobufMessage()
    {
        throw new NotImplementedException();
    }
}

public class TeamChatAgentScaffolding : AgentBase
{
    public TeamChatAgentScaffolding(IAgentRuntime context, EventTypes eventTypes) : base(context, eventTypes)
    {
    }

    public new ValueTask PublishMessageAsync<T>(T message, string? source = null, CancellationToken token = default) where T : ITodoMakeProto
    {
        return base.PublishMessageAsync(message.ToProtobufMessage(), source, token);
    }
}

// This scaffolding is probably unneeded?
public class SequentialRoutedAgent : TeamChatAgentScaffolding
{
    public SequentialRoutedAgent(IAgentRuntime context, EventTypes eventTypes) : base(context, eventTypes)
    {
    }
}
