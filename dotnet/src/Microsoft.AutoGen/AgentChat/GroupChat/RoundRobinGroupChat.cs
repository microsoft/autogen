// Copyright (c) Microsoft Corporation. All rights reserved.
// RoundRobinGroupChat.cs

using Microsoft.AutoGen.Abstractions;

// Copyright (c) Microsoft Corporation. All rights reserved.
// RoundRobinGroupChat.cs

using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.Agents;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public class RoundRobinGroupChatManager : GroupChatManagerBase
{
    private readonly List<string> participantNames;
    //private int currentIndex;

    public RoundRobinGroupChatManager(IAgentRuntime context, EventTypes eventTypes, AgentChatBinder configurator) : base(context, eventTypes, configurator)
    {
        this.participantNames = configurator.ParticipantTopics.ToList();
    }

    public override ValueTask<string> SelectSpeakerAsync(List<AgentMessage> thread)
    {
        throw new NotImplementedException();
    }

    //override Reset()
}

public class RoundRobinGroupChat : GroupChatBase<RoundRobinGroupChatManager>
{
    public RoundRobinGroupChat(List<IChatAgent> participants, ITerminationCondition? terminationCondition = null) : base(participants, terminationCondition)
    {
    }
}
