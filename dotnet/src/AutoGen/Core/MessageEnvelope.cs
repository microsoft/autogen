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

public interface IMessage<out T> : IMessage
{
    T Content { get; }
}

internal class MessageEnvelope<T> : IMessage<T>
{
    public MessageEnvelope(T content, string? from = null, IDictionary<string, object>? metadata = null)
    {
        this.Content = content;
        this.From = from;
        this.Metadata = metadata ?? new Dictionary<string, object>();
    }

    public T Content { get; }

    public string? From { get; set; }

    public IDictionary<string, object> Metadata { get; set; }
}

public class TextMessage : IMessage
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

    public override string ToString()
    {
        return $"TextMessage({this.Role}, {this.Content}, {this.From})";
    }
}

public class ImageMessage : IMessage
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

    public override string ToString()
    {
        return $"ImageMessage({this.Role}, {this.Url}, {this.From})";
    }
}

public class ToolCallMessage : IMessage
{
    public ToolCallMessage(string functionName, string functionArgs, string? from = null)
    {
        this.From = from;
        this.FunctionName = functionName;
        this.FunctionArguments = functionArgs;
    }

    public string FunctionName { get; set; }

    public string FunctionArguments { get; set; }

    public string? From { get; set; }

    public override string ToString()
    {
        return $"ToolCallMessage({this.FunctionName}, {this.FunctionArguments}, {this.From})";
    }
}

public class ToolCallResultMessage : IMessage
{
    public ToolCallResultMessage(string result, ToolCallMessage toolCallMessage, string? from = null)
    {
        this.From = from;
        this.Result = result;
        this.ToolCallMessage = toolCallMessage;
    }

    /// <summary>
    /// The original tool call message
    /// </summary>
    public ToolCallMessage ToolCallMessage { get; set; }

    /// <summary>
    /// The result from the tool call
    /// </summary>
    public string Result { get; set; }

    public string? From { get; set; }

    public override string ToString()
    {
        return $"ToolCallResultMessage({this.Result}, {this.ToolCallMessage}, {this.From})";
    }
}

public class MultiModalMessage : IMessage
{
    public MultiModalMessage(IEnumerable<IMessage> content, string? from = null)
    {
        this.Content = content;
        this.From = from;
        this.Validate();
    }

    public Role Role { get; set; }

    public IEnumerable<IMessage> Content { get; set; }

    public string? From { get; set; }

    private void Validate()
    {
        foreach (var message in this.Content)
        {
            if (message.From != this.From)
            {
                var reason = $"The from property of the message {message} is different from the from property of the aggregate message {this}";
                throw new ArgumentException($"Invalid aggregate message {reason}");
            }
        }

        // all message must be either text or image
        foreach (var message in this.Content)
        {
            if (message is not TextMessage && message is not ImageMessage)
            {
                var reason = $"The message {message} is not a text or image message";
                throw new ArgumentException($"Invalid aggregate message {reason}");
            }
        }
    }

    public override string ToString()
    {
        var stringBuilder = new System.Text.StringBuilder();
        stringBuilder.Append($"MultiModalMessage({this.Role}, {this.From})");
        foreach (var message in this.Content)
        {
            stringBuilder.Append($"\n\t{message}");
        }

        return stringBuilder.ToString();
    }
}

public class ParallelToolCallResultMessage : IMessage
{
    public ParallelToolCallResultMessage(IEnumerable<ToolCallResultMessage> toolCallResult, string? from = null)
    {
        this.ToolCallResult = toolCallResult;
        this.From = from;
        this.Validate();
    }

    public IEnumerable<ToolCallResultMessage> ToolCallResult { get; set; }

    public string? From { get; set; }

    public bool Equals(IMessage other)
    {
        throw new NotImplementedException();
    }

    private void Validate()
    {
        // the from property of all messages should be the same with the from property of the aggregate message
        foreach (var message in this.ToolCallResult)
        {
            if (message.From != this.From)
            {
                var reason = $"The from property of the message {message} is different from the from property of the aggregate message {this}";
                throw new ArgumentException($"Invalid aggregate message {reason}");
            }
        }
    }

    public override string ToString()
    {
        var stringBuilder = new System.Text.StringBuilder();
        stringBuilder.Append($"ParallelToolCallResultMessage({this.From})");
        foreach (var message in this.ToolCallResult)
        {
            stringBuilder.Append($"\n\t{message}");
        }

        return stringBuilder.ToString();
    }
}

public class AggregateMessage : IMessage
{
    public AggregateMessage(IEnumerable<IMessage> messages, string? from = null)
    {
        this.From = from;
        this.Messages = messages;
        this.Validate();
    }

    public IEnumerable<IMessage> Messages { get; set; }

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

    public override string ToString()
    {
        var stringBuilder = new System.Text.StringBuilder();
        stringBuilder.Append($"AggregateMessage({this.From})");
        foreach (var message in this.Messages)
        {
            stringBuilder.Append($"\n\t{message}");
        }

        return stringBuilder.ToString();
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

    public override string ToString()
    {
        return $"Message({this.Role}, {this.Content}, {this.From}, {this.FunctionName}, {this.FunctionArguments})";
    }
}
