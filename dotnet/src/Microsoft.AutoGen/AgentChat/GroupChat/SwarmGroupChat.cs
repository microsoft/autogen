// Copyright (c) Microsoft Corporation. All rights reserved.
// SwarmGroupChat.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public class SwarmGroupChatManager : GroupChatManagerBase
{
    private GroupChatOptions groupOptions;
    private string currentSpeaker;

    public SwarmGroupChatManager(GroupChatOptions groupOptions) : base(groupOptions)
    {
        this.groupOptions = groupOptions;

        this.currentSpeaker = this.groupOptions.Participants.Values.First().TopicType;
    }

    public override ValueTask<string> SelectSpeakerAsync(List<AgentMessage> thread)
    {
        if (thread.Count == 0)
        {
            return ValueTask.FromResult(this.currentSpeaker);
        }

        for (int i = thread.Count - 1; i >= 0; i--)
        {
            if (thread[i] is HandoffMessage handoff)
            {
                this.currentSpeaker = handoff.Target;
                return ValueTask.FromResult(handoff.Target);
            }
        }

        return ValueTask.FromResult(this.currentSpeaker);
    }
}

public class Swarm : GroupChatBase<SwarmGroupChatManager>
{
    public Swarm(List<IChatAgent> participants, ITerminationCondition? terminationCondition = null, int? maxTurns = null) : base(participants, terminationCondition, maxTurns)
    {
        IChatAgent first = participants.First();
        if (!first.ProducedMessageTypes.Contains(typeof(HandoffMessage)))
        {
            throw new InvalidOperationException("The first participant must be able to produce a handoff messages.");
        }
    }
}
