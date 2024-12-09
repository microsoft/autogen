// Copyright (c) Microsoft Corporation. All rights reserved.
// OutputCollectorAgent.cs

using System.Diagnostics;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.AgentChat.GroupChat;
using Microsoft.AutoGen.Agents;
using Microsoft.Extensions.Logging;

namespace Microsoft.AutoGen.AgentChat.Abstractions;

// TODO: Abstract the core logic of this out into the equivalent of ClosureAgent, because that seems like a
// useful facility to have in Core
internal sealed class OutputCollectorAgent : AgentBase,
                                             IHandleEx<GroupChatStart>,
                                             IHandleEx<GroupChatMessage>,
                                             IHandleEx<GroupChatTermination>
{
    public AgentChatBinder binder;

    public OutputCollectorAgent(IAgentRuntime runtime, EventTypes eventTypes, AgentChatBinder binder, ILogger<AgentBase>? logger = null) : base(runtime, eventTypes, logger)
    {
        this.binder = binder;

        this.binder.SubscribeOutput(this);
    }

    private void ForwardMessageInternal(ChatMessage message, CancellationToken cancel = default)
    {
        if (!cancel.IsCancellationRequested)
        {
            // TODO: Catch write failures?
            this.binder.OutputQueue.TryEnqueue(message);
        }
    }

    public ValueTask HandleAsync(GroupChatStart item, CancellationToken cancel)
    {
        if (item.Message != null)
        {
            this.ForwardMessageInternal(item.Message, cancel);
        }

        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(GroupChatMessage item, CancellationToken cancel)
    {
        Debug.Assert(item.Message is ChatMessage, "We should never receive internal messages into the output queue?");
        if (item.Message is ChatMessage chatMessage)
        {
            this.ForwardMessageInternal(chatMessage, cancel);
        }

        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(GroupChatTermination item, CancellationToken cancel)
    {
        this.binder.StopReason = item.Message.Content;
        return ValueTask.CompletedTask;
    }
}
