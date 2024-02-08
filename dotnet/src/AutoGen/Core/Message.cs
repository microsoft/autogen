// Copyright (c) Microsoft Corporation. All rights reserved.
// Message.cs

using System.Collections.Generic;
using Azure.AI.OpenAI;

namespace AutoGen;

public class Message
{
    public Message(
        Role role,
        string? content,
        string? from = null,
        FunctionCall? functionCall = null)
    {
        this.Role = role;
        this.Content = content;
        this.From = from;
        this.FunctionName = functionCall?.Name;
        this.FunctionArguments = functionCall?.Arguments;
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
}
