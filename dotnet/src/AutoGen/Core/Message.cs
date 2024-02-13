// Copyright (c) Microsoft Corporation. All rights reserved.
// Message.cs

using System;
using System.Collections.Generic;
using Azure.AI.OpenAI;

namespace AutoGen;

public interface IMessage
{
    string? From { get; set; }
}

internal class TextMessage : IMessage
{
    public TextMessage(Role role, string content, string? from = null)
    {
        this.Content = content;
        this.Role = role;
        this.From = from;
    }

    public Role Role { get; set; }

    public string Content { get; }

    public string? From { get; set; }

    public bool Equals(IMessage other)
    {
        throw new NotImplementedException();
    }
}

internal class ImageMessage : IMessage
{
    public ImageMessage(Role role, string url, string? from = null)
    {
        this.Role = role;
        this.From = from;
        this.Url = url;
    }

    public Role Role { get; set; }

    public string Url { get; set; }

    public string? From { get; set; }

    public bool Equals(IMessage other)
    {
        throw new NotImplementedException();
    }
}

internal class ToolCallMessage : IMessage
{
    public ToolCallMessage(Role role, string functionName, string functionArgs, string? from = null)
    {
        this.Role = role;
        this.From = from;
        this.FunctionName = functionName;
        this.FunctionArguments = functionArgs;
    }

    public Role Role { get; set; }

    public string FunctionName { get; set; }

    public string FunctionArguments { get; set; }

    public string? From { get; set; }

    public bool Equals(IMessage other)
    {
        throw new NotImplementedException();
    }
}

internal class ToolCallResultMessage : IMessage
{
    public ToolCallResultMessage(Role role, string result, ToolCallMessage toolCallMessage, string? from = null)
    {
        this.Role = role;
        this.From = from;
        this.Result = result;
        this.ToolCallMessage = toolCallMessage;
    }

    public Role Role { get; set; }

    /// <summary>
    /// The original tool call message
    /// </summary>
    public ToolCallMessage ToolCallMessage { get; set; }

    /// <summary>
    /// The result from the tool call
    /// </summary>
    public string Result { get; set; }

    public string? From { get; set; }

    public bool Equals(IMessage other)
    {
        throw new NotImplementedException();
    }
}

internal class AggregateMessage : IMessage
{
    public AggregateMessage(IList<IMessage> messages, string? from = null)
    {
        this.From = from;
        this.Messages = messages;
        this.Validate();
    }

    public IList<IMessage> Messages { get; set; }

    public string? From { get; set; }

    private void Validate()
    {
        // the from property of all messages should be the same with the from property of the aggregate message
        foreach (var message in this.Messages)
        {
            if (message.From != this.From)
            {
                var reason = $"The from property of the message {message} is different from the from property of the aggregate message {this}";
                throw new ArgumentException($"Invalid aggregate message {reason}");
            }
        }

        // no nested aggregate message
        foreach (var message in this.Messages)
        {
            if (message is AggregateMessage)
            {
                var reason = $"The message {message} is an aggregate message";
                throw new ArgumentException("Invalid aggregate message " + reason);
            }
        }
    }

    public bool Equals(IMessage other)
    {
        throw new NotImplementedException();
    }
}

public class Message : IMessage
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
