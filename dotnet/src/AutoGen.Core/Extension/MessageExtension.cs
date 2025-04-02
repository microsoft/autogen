// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System;
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
#pragma warning disable CS0618 // deprecated
            Message msg => msg.FormatMessage(),
#pragma warning restore CS0618 // deprecated
            TextMessage textMessage => textMessage.FormatMessage(),
            ImageMessage imageMessage => imageMessage.FormatMessage(),
            ToolCallMessage toolCallMessage => toolCallMessage.FormatMessage(),
            ToolCallResultMessage toolCallResultMessage => toolCallResultMessage.FormatMessage(),
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => aggregateMessage.FormatMessage(),
            _ => message.ToString(),
        } ?? string.Empty;
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

    [Obsolete("This method is deprecated, please use the extension method FormatMessage(this IMessage message) instead.")]
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
#pragma warning disable CS0618 // deprecated
            Message msg => msg.Role == Role.System,
#pragma warning restore CS0618 // deprecated
            _ => false,
        };
    }

    /// <summary>
    /// Get the content from the message
    /// <para>if the message implements <see cref="ICanGetTextContent"/>, return the content from the message by calling <see cref="ICanGetTextContent.GetContent()"/></para>
    /// <para>if the message is a <see cref="AggregateMessage{ToolCallMessage, ToolCallResultMessage}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/> and the second message only contains one function call, return the result of that function call</para>
    /// <para>for all other situation, return null.</para>
    /// </summary>
    /// <param name="message"></param>
    public static string? GetContent(this IMessage message)
    {
        return message switch
        {
            ICanGetTextContent canGetTextContent => canGetTextContent.GetContent(),
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => string.Join("\n", aggregateMessage.Message2.ToolCalls.Where(x => x.Result is not null).Select(x => x.Result)),
#pragma warning disable CS0618 // deprecated
            Message msg => msg.Content,
#pragma warning restore CS0618 // deprecated
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
#pragma warning disable CS0618 // deprecated
            Message msg => msg.Role,
#pragma warning restore CS0618 // deprecated
            ImageMessage img => img.Role,
            MultiModalMessage multiModal => multiModal.Role,
            _ => null,
        };
    }

    /// <summary>
    /// Return the tool calls from the message if it's available.
    /// <para>if the message implements <see cref="ICanGetToolCalls"/>, return the tool calls from the message by calling <see cref="ICanGetToolCalls.GetToolCalls()"/></para>
    /// <para>if the message is a <see cref="AggregateMessage{ToolCallMessage, ToolCallResultMessage}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/>, return the tool calls from the first message</para>
    /// </summary>
    /// <param name="message"></param>
    /// <returns></returns>
    public static IList<ToolCall>? GetToolCalls(this IMessage message)
    {
        return message switch
        {
            ICanGetToolCalls canGetToolCalls => canGetToolCalls.GetToolCalls().ToList(),
#pragma warning disable CS0618 // deprecated
            Message msg => msg.FunctionName is not null && msg.FunctionArguments is not null
                ? msg.Content is not null ? [new ToolCall(msg.FunctionName, msg.FunctionArguments, result: msg.Content)]
                : new List<ToolCall> { new(msg.FunctionName, msg.FunctionArguments) }
                : null,
#pragma warning restore CS0618 // deprecated
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => aggregateMessage.Message1.ToolCalls,
            _ => null,
        };
    }
}
