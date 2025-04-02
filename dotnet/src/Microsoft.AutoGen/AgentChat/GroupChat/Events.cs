// Copyright (c) Microsoft Corporation. All rights reserved.
// Events.cs

using Microsoft.AutoGen.AgentChat.Abstractions;

// using ProtobufTypeMarshal = Microsoft.AutoGen.AgentChat.WireProtocol.ProtobufTypeMarshal;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public class GroupChatEventBase /*: IWireable*/
{
    // public IMessage ToWire()
    // {
    //     return this switch
    //     {
    //         GroupChatStart groupChatStart => ProtobufTypeMarshal.Convert<GroupChatStart, WireProtocol.GroupChatStart>(groupChatStart),
    //         GroupChatAgentResponse groupChatAgentResponse => ProtobufTypeMarshal.Convert<GroupChatAgentResponse, WireProtocol.GroupChatResponse>(groupChatAgentResponse),
    //         GroupChatRequestPublish groupChatRequestPublish => ProtobufTypeMarshal.Convert<GroupChatRequestPublish, WireProtocol.GroupChatRequestPublish>(groupChatRequestPublish),
    //         GroupChatMessage groupChatMessage => ProtobufTypeMarshal.Convert<GroupChatMessage, WireProtocol.GroupChatMessage>(groupChatMessage),
    //         GroupChatTermination groupChatTermination => ProtobufTypeMarshal.Convert<GroupChatTermination, WireProtocol.GroupChatTermination>(groupChatTermination),
    //         GroupChatReset groupChatReset => ProtobufTypeMarshal.Convert<GroupChatReset, WireProtocol.GroupChatReset>(groupChatReset),
    //         _ => throw new InvalidOperationException($"Unknown type {this.GetType().Name}"),
    //     };
    // }
}

/// <summary>
/// A request to start a group chat.
/// </summary>
public class GroupChatStart : GroupChatEventBase
{
    /// <summary>
    /// An optional list of messages to start the group chat.
    /// </summary>
    public List<ChatMessage>? Messages { get; set; }
}

/// <summary>
/// A response published to a group chat.
/// </summary>
public class GroupChatAgentResponse : GroupChatEventBase
{
    /// <summary>
    /// The response from a agent.
    /// </summary>
    public required Response AgentResponse { get; set; }
}

/// <summary>
/// A request to publish a message to a group chat.
/// </summary>
public class GroupChatRequestPublish : GroupChatEventBase
{
}

/// <summary>
/// A message from a group chat.
/// </summary>
public class GroupChatMessage : GroupChatEventBase
{
    /// <summary>
    /// The message that was published.
    /// </summary>
    public required AgentMessage Message { get; set; }
}

/// <summary>
/// A message indicating that group chat was terminated.
/// </summary>
public class GroupChatTermination : GroupChatEventBase
{
    /// <summary>
    /// The stop message that indicates the reason of termination.
    /// </summary>
    public required StopMessage Message { get; set; }
}

/// <summary>
/// A request to reset the agents in the group chat.
/// </summary>
public class GroupChatReset : GroupChatEventBase
{
}

