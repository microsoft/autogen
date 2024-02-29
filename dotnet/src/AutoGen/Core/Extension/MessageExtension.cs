// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace AutoGen;

public static class MessageExtension
{
    private static string separator = new string('-', 20);

    public static string FormatMessage(this IMessage message)
    {
        return message switch
        {
            Message msg => msg.FormatMessage(),
            _ => message.ToString(),
        };
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
    /// </summary>
    /// <param name="message"></param>
    public static string? GetContent(this IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => textMessage.Content,
            Message msg => msg.Content,
            ToolCallResultMessage toolCallResultMessage => toolCallResultMessage.GetToolCalls().Count() == 1 ? toolCallResultMessage.GetToolCalls().First().Result : null,
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

    public static IEnumerable<ToolCall> GetToolCalls(this IMessage message)
    {
        return message switch
        {
            ToolCallMessage toolCallMessage => toolCallMessage.ToolCalls,
            ToolCallResultMessage toolCallResultMessage => toolCallResultMessage.ToolCalls,
            Message msg => msg.FunctionName is not null && msg.FunctionArguments is not null
                ? msg.Content is not null ? new List<ToolCall> { new ToolCall(msg.FunctionName, msg.FunctionArguments, result: msg.Content) }
                : new List<ToolCall> { new ToolCall(msg.FunctionName, msg.FunctionArguments) }
                : [],
            _ => [],
        };
    }
}
