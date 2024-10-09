// Copyright (c) Microsoft Corporation. All rights reserved.
// IMessage.cs

using System;
using System.Collections.Generic;

namespace AutoGen.Core;

/// <summary>
/// The universal message interface for all message types in AutoGen.
/// <para>Related PR: https://github.com/microsoft/autogen/pull/1676</para>
/// <para>Built-in message types</para>
/// <list type="bullet">
/// <item>
/// <see cref="TextMessage"/>: plain text message.
/// </item>
/// <item>
/// <see cref="ImageMessage"/>: image message.
/// </item>
/// <item>
/// <see cref="MultiModalMessage"/>: message type for multimodal message. The current support message items are <see cref="TextMessage"/> and <see cref="ImageMessage"/>.
/// </item>
/// <item>
/// <see cref="ToolCallMessage"/>: message type for tool call. This message supports both single and parallel tool call.
/// </item>
/// <item>
/// <see cref="ToolCallResultMessage"/>: message type for tool call result.
/// </item>
/// <item>
/// <see cref="Message"/>: This type is used by previous version of AutoGen. And it's reserved for backward compatibility.
/// </item>
/// <item>
/// <see cref="AggregateMessage{TMessage1, TMessage2}"/>: an aggregate message type that contains two message types.
/// This type is useful when you want to combine two message types into one unique message type. One example is when invoking a tool call and you want to return both <see cref="ToolCallMessage"/> and <see cref="ToolCallResultMessage"/>.
/// One example of how this type is used in AutoGen is <see cref="FunctionCallMiddleware"/> and its return message <see cref="ToolCallAggregateMessage"/>
/// </item>
/// </list>
/// </summary>
public interface IMessage
{
    string? From { get; set; }
}

public interface IMessage<out T> : IMessage
{
    T Content { get; }
}

/// <summary>
/// The interface for messages that can get text content.
/// This interface will be used by <see cref="MessageExtension.GetContent(IMessage)"/> to get the content from the message.
/// </summary>
public interface ICanGetTextContent : IMessage
{
    public string? GetContent();
}

/// <summary>
/// The interface for messages that can get a list of <see cref="ToolCall"/>
/// </summary>
public interface ICanGetToolCalls : IMessage
{
    public IEnumerable<ToolCall> GetToolCalls();
}

[Obsolete("Use IMessage instead")]
public interface IStreamingMessage
{
    string? From { get; set; }
}

[Obsolete("Use IMessage<T> instead")]
public interface IStreamingMessage<out T> : IStreamingMessage
{
    T Content { get; }
}
