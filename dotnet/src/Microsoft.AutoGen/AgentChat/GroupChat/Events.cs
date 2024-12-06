// Copyright (c) Microsoft Corporation. All rights reserved.
// Events.cs

//using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.AgentChat.Abstractions;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public class GroupChatEventBase : ITodoMakeProto
{
}

/// <summary>
/// A request to start a group chat.
/// </summary>
public class GroupChatStart : GroupChatEventBase
{
    /// <summary>
    /// The user message that started the group chat.
    /// </summary>
    public ChatMessage? Message { get; set; }
}

public class GroupChatAgentResponse : GroupChatEventBase
{
    public required Response AgentResponse { get; set; }
}

public class GroupChatRequestPublish : GroupChatEventBase
{
}

public class GroupChatMessage : GroupChatEventBase
{
    public required AgentMessage Message { get; set; }
}

public class GroupChatTermination : GroupChatEventBase
{
    public required StopMessage Message { get; set; }
}

public class GroupChatReset : GroupChatEventBase
{
}

///// <summary>
///// 
///// </summary>
///// <remarks>
///// Corresponds to Python-side `GroupChatPublicEvent` class, defined in `src/Microsoft.AutoGen/AgentChat/Teams/Events.py`.
///// </remarks>
//public class GroupChatPublicEvent
//{
//    public ChatMessage AgentMessage { get; set; }

//    public AgentId? Source { get; set; }

//    public IDictionary<string, string> ModelConfig { get; }

//    public GroupChatPublicEvent(ChatMessage agentMessage, AgentId? source, IDictionary<string, string> modelConfig)
//    {
//        AgentMessage = agentMessage;
//        Source = source;
//        ModelConfig = modelConfig;
//    }
//}

