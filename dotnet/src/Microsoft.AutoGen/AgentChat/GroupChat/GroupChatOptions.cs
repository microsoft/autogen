// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatOptions.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public struct GroupParticipant(string topicType, string description)
{
    public string TopicType { get; } = topicType;
    public string Description { get; } = description;

    // Destructuring from a tuple
    public GroupParticipant((string topicType, string description) tuple) : this(tuple.topicType, tuple.description)
    {
    }

    // Destructuring to a tuple
    public void Deconstruct(out string topicType, out string description)
    {
        topicType = this.TopicType;
        description = this.Description;
    }

    public static implicit operator GroupParticipant((string topicType, string description) tuple) => new GroupParticipant(tuple);
    public static implicit operator (string topicType, string description)(GroupParticipant participant) => (participant.TopicType, participant.Description);
}

public class GroupChatOptions(string groupTopicType, string outputTopicType)
{
    public string GroupChatTopicType { get; } = groupTopicType;
    public string OutputTopicType { get; } = outputTopicType;

    public ITerminationCondition? TerminationCondition { get; set; }
    public int? MaxTurns { get; set; }

    public Dictionary<string, GroupParticipant> Participants { get; } = new Dictionary<string, GroupParticipant>();
}
