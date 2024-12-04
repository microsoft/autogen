// Copyright (c) Microsoft Corporation. All rights reserved.
// Events.cs

using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

/// <summary>
/// A request to start a group chat.
/// </summary>
public class GroupChatStart
{
    /// <summary>
    /// The user message that started the group chat.
    /// </summary>
    public required ChatMessage Message { get; set; }
}

public class GroupChatAgentResponse
{
    public required Response AgentResponse { get; set; }
}

public class GroupChatRequestPublish
{
}

public class GroupChatMessage
{
    public required AgentMessage Message { get; set; }
}

public class GroupChatTermination
{
    public required StopMessage Message { get; set; }
}

public class  GroupChatReset
{
}

/// <summary>
/// 
/// </summary>
/// <remarks>
/// Corresponds to Python-side `GroupChatPublicEvent` class, defined in `src/Microsoft.AutoGen/AgentChat/Teams/Events.py`.
/// </remarks>
public class GroupChatPublicEvent
{
    public ChatMessage AgentMessage { get; set; }

    public AgentId? Source { get; set; }

    public IDictionary<string, string> ModelConfig { get; }

    public GroupChatPublicEvent(ChatMessage agentMessage, AgentId? source, IDictionary<string, string> modelConfig)
    {
        AgentMessage = agentMessage;
        Source = source;
        ModelConfig = modelConfig;
    }
}

