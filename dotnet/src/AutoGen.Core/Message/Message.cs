// Copyright (c) Microsoft Corporation. All rights reserved.
// Message.cs

using System;
using System.Collections.Generic;

namespace AutoGen.Core;

[Obsolete("This message class is deprecated, please use a specific AutoGen built-in message type instead. For more information, please visit https://microsoft.github.io/autogen-for-net/articles/Built-in-messages.html")]
public class Message : IMessage
{
    public Message(
        Role role,
        string? content,
        string? from = null,
        ToolCall? toolCall = null)
    {
        this.Role = role;
        this.Content = content;
        this.From = from;
        this.FunctionName = toolCall?.FunctionName;
        this.FunctionArguments = toolCall?.FunctionArguments;
    }

    public Message(Message other)
        : this(other.Role, other.Content, other.From)
    {
        this.FunctionName = other.FunctionName;
        this.FunctionArguments = other.FunctionArguments;
        this.Value = other.Value;
        this.Metadata = other.Metadata;
    }

    public Role Role { get; set; }

    public string? Content { get; set; }

    public string? From { get; set; }

    public string? FunctionName { get; set; }

    public string? FunctionArguments { get; set; }

    /// <summary>
    /// raw message
    /// </summary>
    public object? Value { get; set; }

    public IList<KeyValuePair<string, object>> Metadata { get; set; } = new List<KeyValuePair<string, object>>();

    public override string ToString()
    {
        return $"Message({this.Role}, {this.Content}, {this.From}, {this.FunctionName}, {this.FunctionArguments})";
    }
}
