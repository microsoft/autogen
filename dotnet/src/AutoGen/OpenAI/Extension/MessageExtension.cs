// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System;
using System.Collections.Generic;
using System.Linq;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI;

public static class MessageExtension
{
    public static string TEXT_CONTENT_TYPE = "text";
    public static string IMAGE_CONTENT_TYPE = "image";

    public static Message ToMessage(this ChatRequestMessage message)
    {
        if (message is ChatRequestUserMessage userMessage)
        {
            var msg = new Message(Role.User, userMessage.Content)
            {
                Value = message,
            };

            if (userMessage.MultimodalContentItems != null)
            {
                foreach (var item in userMessage.MultimodalContentItems)
                {
                    if (item is ChatMessageTextContentItem textItem)
                    {
                        msg.Metadata.Add(new KeyValuePair<string, object>(TEXT_CONTENT_TYPE, textItem.Text));
                    }
                    else if (item is ChatMessageImageContentItem imageItem)
                    {
                        msg.Metadata.Add(new KeyValuePair<string, object>(IMAGE_CONTENT_TYPE, imageItem.ImageUrl.Url.OriginalString));
                    }
                }
            }

            return msg;
        }
        else if (message is ChatRequestAssistantMessage assistantMessage)
        {
            return new Message(Role.Assistant, assistantMessage.Content)
            {
                Value = message,
                FunctionArguments = assistantMessage.FunctionCall?.Arguments,
                FunctionName = assistantMessage.FunctionCall?.Name,
                From = assistantMessage.Name,
            };
        }
        else if (message is ChatRequestSystemMessage systemMessage)
        {
            return new Message(Role.System, systemMessage.Content)
            {
                Value = message,
                From = systemMessage.Name,
            };
        }
        else if (message is ChatRequestFunctionMessage functionMessage)
        {
            return new Message(Role.Function, functionMessage.Content)
            {
                Value = message,
                FunctionName = functionMessage.Name,
            };
        }
        else
        {
            throw new ArgumentException($"Unknown message type: {message.GetType()}");
        }
    }

    public static ChatRequestUserMessage ToChatRequestUserMessage(this Message message)
    {
        if (message.Value is ChatRequestUserMessage message1)
        {
            return message1;
        }
        else if (message?.Metadata is { Count: > 0 })
        {
            var itemList = new List<ChatMessageContentItem>();
            foreach (var item in message.Metadata)
            {
                if (item.Key == TEXT_CONTENT_TYPE && item.Value is string txt)
                {
                    itemList.Add(new ChatMessageTextContentItem(txt));
                }
                else if (item.Key == IMAGE_CONTENT_TYPE && item.Value is string url)
                {
                    itemList.Add(new ChatMessageImageContentItem(new Uri(url)));
                }
            }

            if (itemList.Count > 0)
            {
                return new ChatRequestUserMessage(itemList);
            }
            else
            {
                throw new ArgumentException("Content is null and metadata is null");
            }
        }
        else if (!string.IsNullOrEmpty(message?.Content))
        {
            return new ChatRequestUserMessage(message!.Content);
        }

        throw new ArgumentException("Content is null and metadata is null");
    }

    public static ChatRequestAssistantMessage ToChatRequestAssistantMessage(this Message message)
    {
        if (message.Value is ChatRequestAssistantMessage message1)
        {
            return message1;
        }

        var assistantMessage = new ChatRequestAssistantMessage(message.Content ?? string.Empty);
        if (message.FunctionName != null && message.FunctionArguments != null)
        {
            assistantMessage.FunctionCall = new FunctionCall(message.FunctionName, message.FunctionArguments ?? string.Empty);
        }

        return assistantMessage;
    }

    public static ChatRequestSystemMessage ToChatRequestSystemMessage(this Message message)
    {
        if (message.Value is ChatRequestSystemMessage message1)
        {
            return message1;
        }

        if (message.Content is null)
        {
            throw new ArgumentException("Content is null");
        }

        var systemMessage = new ChatRequestSystemMessage(message.Content);

        return systemMessage;
    }

    public static ChatRequestFunctionMessage ToChatRequestFunctionMessage(this Message message)
    {
        if (message.Value is ChatRequestFunctionMessage message1)
        {
            return message1;
        }

        if (message.FunctionName is null)
        {
            throw new ArgumentException("FunctionName is null");
        }

        if (message.Content is null)
        {
            throw new ArgumentException("Content is null");
        }

        var functionMessage = new ChatRequestFunctionMessage(message.FunctionName, message.Content);

        return functionMessage;
    }

    public static IEnumerable<ChatRequestMessage> ToOpenAIChatRequestMessage(this IAgent agent, IMessage message)
    {
        if (message.From != agent.Name)
        {
            if (message is TextMessage textMessage)
            {
                if (textMessage.Role == Role.System)
                {
                    return [new ChatRequestSystemMessage(textMessage.Content)];
                }
                else
                {
                    return [new ChatRequestUserMessage(textMessage.Content)];
                }
            }
            else if (message is ToolCallMessage)
            {
                throw new ArgumentException($"ToolCallMessage is not supported when message.From is not the same with agent");
            }
            else if (message is ToolCallResultMessage toolCallResult)
            {
                return [new ChatRequestToolMessage(toolCallResult.Result, toolCallResult.ToolCallMessage.FunctionName)];
            }
            else if (message is AggregateMessage aggregateMessage)
            {
                // if aggreate message contains a list of tool call result message, then it is a parallel tool call message
                if (aggregateMessage.Messages.All(m => m is ToolCallResultMessage))
                {
                    return aggregateMessage.Messages.Select(message => new ChatRequestToolMessage((message as ToolCallResultMessage)!.Result, (message as ToolCallResultMessage)!.ToolCallMessage.FunctionName));
                }

                // otherwise, it's a multi-modal message
                IEnumerable<ChatMessageContentItem> messageContent = aggregateMessage.Messages.Select<IMessage, ChatMessageContentItem>(m =>
                {
                    return m switch
                    {
                        TextMessage textMessage => new ChatMessageTextContentItem(textMessage.Content),
                        ImageMessage imageMessage => new ChatMessageImageContentItem(new Uri(imageMessage.Url)),
                        _ => throw new ArgumentException($"Unknown message type: {m.GetType()}")
                    };
                });

                return [new ChatRequestUserMessage(messageContent)];
            }
            else
            {
                throw new ArgumentException($"Unknown message type: {message.GetType()}");
            }
        }
        else
        {
            if (message is TextMessage textMessage)
            {
                if (textMessage.Role == Role.System)
                {
                    throw new ArgumentException("System message is not supported when message.From is the same with agent");
                }

                return [new ChatRequestAssistantMessage(textMessage.Content)];
            }
            else if (message is ToolCallMessage toolCallMessage)
            {
                // single tool call message
                var assistantMessage = new ChatRequestAssistantMessage(string.Empty);
                assistantMessage.ToolCalls.Add(new ChatCompletionsFunctionToolCall(toolCallMessage.FunctionName, toolCallMessage.FunctionName, toolCallMessage.FunctionArguments));

                return [assistantMessage];
            }
            else if (message is AggregateMessage aggregateMessage)
            {
                // parallel tool call messages
                var assistantMessage = new ChatRequestAssistantMessage(string.Empty);
                foreach (var m in aggregateMessage.Messages)
                {
                    if (m is ToolCallMessage toolCall)
                    {
                        assistantMessage.ToolCalls.Add(new ChatCompletionsFunctionToolCall(toolCall.FunctionName, toolCall.FunctionName, toolCall.FunctionArguments));
                    }
                    else
                    {
                        throw new ArgumentException($"Unknown message type: {m.GetType()}");
                    }
                }

                return [assistantMessage];
            }
            else
            {
                throw new ArgumentException($"Unknown message type: {message.GetType()}");
            }
        }
    }
}
