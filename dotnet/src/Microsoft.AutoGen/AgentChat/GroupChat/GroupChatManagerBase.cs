// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatManagerBase.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public class GroupChatOptions
{
    public ITerminationCondition? TerminationCondition { get; set; }
}

public abstract class GroupChatManagerBase : IHandleChat<GroupChatStart>,
                                             IHandleChat<GroupChatAgentResponse>,
                                             IHandleDefault
{
    public string Description => "Group chat manager";

    // It is kind of annoying that all child classes need to be aware of all of these objects to go up the stack
    // TODO: Should we replace all of these with IServiceCollection?
    public GroupChatManagerBase()
    {
    }

    protected virtual async ValueTask ValidateGroupState(List<ChatMessage>? messages)
    {
    }

    public abstract ValueTask<string> SelectSpeakerAsync(List<AgentMessage> thread);

    public ValueTask HandleAsync(GroupChatStart wireItem, CancellationToken cancellationToken)
    {
        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(GroupChatAgentResponse wireItem, CancellationToken cancellationToken)
    {
        return ValueTask.CompletedTask;
    }

    public ValueTask HandleAsync(object item, CancellationToken cancellationToken)
    {
        throw new InvalidOperationException($"Unhandled message in group chat manager: {item.GetType()}");
    }
}
