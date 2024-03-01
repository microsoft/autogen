// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace AutoGen.Core;

public static class MessageExtension
{
    private static string separator = new string('-', 20);

    public static string FormatMessage(this IMessage message)
    {
        return message switch
        {
            Message msg => msg.FormatMessage(),
            TextMessage textMessage => textMessage.FormatMessage(),
            ImageMessage imageMessage => imageMessage.FormatMessage(),
            ToolCallMessage toolCallMessage => toolCallMessage.FormatMessage(),
            ToolCallResultMessage toolCallResultMessage => toolCallResultMessage.FormatMessage(),
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => aggregateMessage.FormatMessage(),
            _ => message.ToString(),
        };
    }

    public static string FormatMessage(this TextMessage message)
    {
        var sb = new StringBuilder();
        // write from
        sb.AppendLine($"TextMessage from {message.From}");
        // write a seperator
        sb.AppendLine(separator);
        sb.AppendLine(message.Content);
        // write a seperator
        sb.AppendLine(separator);

        return sb.ToString();
    }

    public static string FormatMessage(this ImageMessage message)
    {
        var sb = new StringBuilder();
        // write from
        sb.AppendLine($"ImageMessage from {message.From}");
        // write a seperator
        sb.AppendLine(separator);
        sb.AppendLine($"Image: {message.Url}");
        // write a seperator
        sb.AppendLine(separator);

        return sb.ToString();
    }

    public static string FormatMessage(this ToolCallMessage message)
    {
        var sb = new StringBuilder();
        // write from
        sb.AppendLine($"ToolCallMessage from {message.From}");

        // write a seperator
        sb.AppendLine(separator);

        foreach (var toolCall in message.ToolCalls)
        {
            sb.AppendLine($"- {toolCall.FunctionName}: {toolCall.FunctionArguments}");
        }

        sb.AppendLine(separator);

        return sb.ToString();
    }

    public static string FormatMessage(this ToolCallResultMessage message)
    {
        var sb = new StringBuilder();
        // write from
        sb.AppendLine($"ToolCallResultMessage from {message.From}");

        // write a seperator
        sb.AppendLine(separator);

        foreach (var toolCall in message.ToolCalls)
        {
            sb.AppendLine($"- {toolCall.FunctionName}: {toolCall.Result}");
        }

        sb.AppendLine(separator);

        return sb.ToString();
    }

    public static string FormatMessage(this AggregateMessage<ToolCallMessage, ToolCallResultMessage> message)
    {
        var sb = new StringBuilder();
        // write from
        sb.AppendLine($"AggregateMessage from {message.From}");

        // write a seperator
        sb.AppendLine(separator);

        sb.AppendLine("ToolCallMessage:");
        sb.AppendLine(message.Message1.FormatMessage());

        sb.AppendLine("ToolCallResultMessage:");
        sb.AppendLine(message.Message2.FormatMessage());

        sb.AppendLine(separator);

        return sb.ToString();
    }
    public static string FormatMessage(this Message message)
    {
        var sb = new StringBuilder();
        // write from
        sb.AppendLine($"Message from {message.From}");
        // write a seperator
        sb.AppendLine(separator);

        // write content
        sb.AppendLine($"content: {message.Content}");

        // write function name if exists
        if (!string.IsNullOrEmpty(message.FunctionName))
        {
            sb.AppendLine($"function name: {message.FunctionName}");
            sb.AppendLine($"function arguments: {message.FunctionArguments}");
        }

        // write metadata
        if (message.Metadata is { Count: > 0 })
        {
            sb.AppendLine($"metadata:");
            foreach (var item in message.Metadata)
            {
                sb.AppendLine($"{item.Key}: {item.Value}");
            }
        }

        // write a seperator
        sb.AppendLine(separator);

        return sb.ToString();
    }

    public static bool IsSystemMessage(this IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => textMessage.Role == Role.System,
            Message msg => msg.Role == Role.System,
            _ => false,
        };
    }

    /// <summary>
    /// Get the content from the message
    /// <para>if the message is a <see cref="Message"/> or <see cref="TextMessage"/>, return the content</para>
    /// <para>if the message is a <see cref="ToolCallResultMessage"/> and only contains one function call, return the result of that function call</para>
    /// <para>if the message is a <see cref="AggregateMessage{ToolCallMessage, ToolCallResultMessage}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/> and the second message only contains one function call, return the result of that function call</para>
    /// <para>for all other situation, return null.</para>
    /// </summary>
    /// <param name="message"></param>
    public static string? GetContent(this IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => textMessage.Content,
            Message msg => msg.Content,
            ToolCallResultMessage toolCallResultMessage => toolCallResultMessage.ToolCalls.Count == 1 ? toolCallResultMessage.ToolCalls.First().Result : null,
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => aggregateMessage.Message2.ToolCalls.Count == 1 ? aggregateMessage.Message2.ToolCalls.First().Result : null,
            _ => null,
        };
    }

    /// <summary>
    /// Get the role from the message if it's available.
    /// </summary>
    public static Role? GetRole(this IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => textMessage.Role,
            Message msg => msg.Role,
            ImageMessage img => img.Role,
            MultiModalMessage multiModal => multiModal.Role,
            _ => null,
        };
    }

    /// <summary>
    /// Return the tool calls from the message if it's available.
    /// <para>if the message is a <see cref="ToolCallMessage"/>, return its tool calls</para>
    /// <para>if the message is a <see cref="Message"/> and the function name and function arguments are available, return a list of tool call with one item</para>
    /// <para>if the message is a <see cref="AggregateMessage{ToolCallMessage, ToolCallResultMessage}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/>, return the tool calls from the first message</para>
    /// </summary>
    /// <param name="message"></param>
    /// <returns></returns>
    public static IList<ToolCall>? GetToolCalls(this IMessage message)
    {
        return message switch
        {
            ToolCallMessage toolCallMessage => toolCallMessage.ToolCalls,
            Message msg => msg.FunctionName is not null && msg.FunctionArguments is not null
                ? msg.Content is not null ? new List<ToolCall> { new ToolCall(msg.FunctionName, msg.FunctionArguments, result: msg.Content) }
                : new List<ToolCall> { new ToolCall(msg.FunctionName, msg.FunctionArguments) }
                : null,
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => aggregateMessage.Message1.ToolCalls,
            _ => null,
        };
    }
}
