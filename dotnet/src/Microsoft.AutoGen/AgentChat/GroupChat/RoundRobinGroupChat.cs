// Copyright (c) Microsoft Corporation. All rights reserved.
// RoundRobinGroupChat.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

/// <summary>
/// A group chat manager that selects the next speaker in a round-robin fashion.
/// </summary>
public class RoundRobinGroupChatManager : GroupChatManagerBase
{
    private readonly List<string> participantTopicTypes;
    private int nextSpeakerIndex;

    public RoundRobinGroupChatManager(GroupChatOptions options) : base(options)
    {
        this.participantTopicTypes = [.. from candidateTopic in options.Participants.Values
                                         select candidateTopic.TopicType];
        this.nextSpeakerIndex = 0;
    }

    public override ValueTask<string> SelectSpeakerAsync(List<AgentMessage> thread)
    {
        string result = this.participantTopicTypes[this.nextSpeakerIndex].ToString();

        this.nextSpeakerIndex = (this.nextSpeakerIndex + 1) % this.participantTopicTypes.Count;

        return ValueTask.FromResult(result);
    }
}

/// <summary>
/// A team that runs a group chat with a participants taking turns in a round-robin fashion to publish
/// a message to all.
///
/// If a single participant is in the team, the participant will be the only speaker.
/// </summary>
public class RoundRobinGroupChat : GroupChatBase<RoundRobinGroupChatManager>
{
    /// <summary>
    /// Initializes a new round-robin group chat.
    /// </summary>
    /// <param name="participants">The participants in the group chat.</param>
    /// <param name="terminationCondition">
    /// The termination condition for the group chat. Defaults to <c>null</c>. Without a termination 
    /// condition, the group chat will run indefinitely.
    /// </param>
    /// <param name="maxTurns">
    /// The maximum number of turns for the group chat. Defaults to <c>null</c>, meaning no limit.
    /// Note that the <see cref="ITerminationCondition"/> gets first priority for checking the termination
    /// if both are provided.
    /// </param>
    public RoundRobinGroupChat(List<IChatAgent> participants, ITerminationCondition? terminationCondition = null, int? maxTurns = null) : base(participants, terminationCondition, maxTurns)
    {
    }
}
