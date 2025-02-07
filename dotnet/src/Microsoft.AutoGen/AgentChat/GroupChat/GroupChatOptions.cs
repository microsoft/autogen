// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatOptions.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public class GroupChatOptions(string groupTopicType, string outputTopicType)
{
    public string GroupChatTopicType { get; } = groupTopicType;
    public string OutputTopicType { get; } = outputTopicType;

    public ITerminationCondition? TerminationCondition { get; set; }
    public int? MaxTurns { get; set; }

    public Dictionary<string, (string TopicType, string Description)> Participants { get; } = new Dictionary<string, (string, string)>();
}
