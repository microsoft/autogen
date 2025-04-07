// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatAgentContainerState.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.State;

public class ChatAgentContainerState : BaseState
{
    public required SerializedState AgentState { get; set; }
    public List<ChatMessage> MessageBuffer { get; set; } = new();
}

public class GroupChatManagerStateBase : BaseState
{
    public List<AgentMessage> MessageThread { get; set; } = new();
    public int CurrentTurn { get; set; }
}

public class RoundRobinManagerState : GroupChatManagerStateBase
{
    public int NextSpeakerIndex { get; set; }
}
