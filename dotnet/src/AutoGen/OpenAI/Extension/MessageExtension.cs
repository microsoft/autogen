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
        if (message is IMessage<ChatRequestMessage> oaiMessage)
        {
            // short-circuit
            return [oaiMessage.Content];
        }

        if (message.From != agent.Name)
        {
            if (message is TextMessage textMessage)
            {
                if (textMessage.Role == Role.System)
                {
                    var msg = new ChatRequestSystemMessage(textMessage.Content);

                    return [msg];
                }
                else
                {
                    var msg = new ChatRequestUserMessage(textMessage.Content);
                    return [msg];
                }
            }
            else if (message is ImageMessage imageMessage)
            {
                // multi-modal
                var msg = new ChatRequestUserMessage(new ChatMessageImageContentItem(new Uri(imageMessage.Url)));

                return [msg];
            }
            else if (message is ToolCallMessage)
            {
                throw new ArgumentException($"ToolCallMessage is not supported when message.From is not the same with agent");
            }
            else if (message is ToolCallResultMessage toolCallResult)
            {
                return toolCallResult.ToolCalls.Select(m =>
                {
                    var msg = new ChatRequestToolMessage(m.Result, m.FunctionName);

                    return msg;
                });
            }
            else if (message is MultiModalMessage multiModalMessage)
            {
                var messageContent = multiModalMessage.Content.Select<IMessage, ChatMessageContentItem>(m =>
                {
                    return m switch
                    {
                        TextMessage textMessage => new ChatMessageTextContentItem(textMessage.Content),
                        ImageMessage imageMessage => new ChatMessageImageContentItem(new Uri(imageMessage.Url)),
                        _ => throw new ArgumentException($"Unknown message type: {m.GetType()}")
                    };
                });

                var msg = new ChatRequestUserMessage(messageContent);
                return [msg];
            }
            else if (message is AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage)
            {
                // convert as user message
                var resultMessage = aggregateMessage.Message2;
                return resultMessage.ToolCalls.Select(m => new ChatRequestUserMessage(m.Result));
            }
            else if (message is Message msg)
            {
                if (msg.Role == Role.System)
                {
                    var systemMessage = new ChatRequestSystemMessage(msg.Content ?? string.Empty);
                    return [systemMessage];
                }
                else if (msg.FunctionName is null && msg.FunctionArguments is null)
                {
                    var userMessage = msg.ToChatRequestUserMessage();
                    return [userMessage];
                }
                else if (msg.FunctionName is not null && msg.FunctionArguments is not null && msg.Content is not null)
                {
                    if (msg.Role == Role.Function)
                    {
                        return [new ChatRequestFunctionMessage(msg.FunctionName, msg.Content)];
                    }
                    else
                    {
                        return [new ChatRequestUserMessage(msg.Content)];
                    }
                }
                else
                {
                    var userMessage = new ChatRequestUserMessage(msg.Content ?? throw new ArgumentException("Content is null"));
                    return [userMessage];
                }
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
                var assistantMessage = new ChatRequestAssistantMessage(string.Empty);
                var toolCalls = toolCallMessage.ToolCalls.Select(tc => new ChatCompletionsFunctionToolCall(tc.FunctionName, tc.FunctionName, tc.FunctionArguments));
                foreach (var tc in toolCalls)
                {
                    assistantMessage.ToolCalls.Add(tc);
                }

                return [assistantMessage];
            }
            else if (message is AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage)
            {
                var toolCallMessage1 = aggregateMessage.Message1;
                var toolCallResultMessage = aggregateMessage.Message2;

                var assistantMessage = new ChatRequestAssistantMessage(string.Empty);
                var toolCalls = toolCallMessage1.ToolCalls.Select(tc => new ChatCompletionsFunctionToolCall(tc.FunctionName, tc.FunctionName, tc.FunctionArguments));
                foreach (var tc in toolCalls)
                {
                    assistantMessage.ToolCalls.Add(tc);
                }

                var toolCallResults = toolCallResultMessage.ToolCalls.Select(tc => new ChatRequestToolMessage(tc.Result, tc.FunctionName));

                // return assistantMessage and tool call result messages
                var messages = new List<ChatRequestMessage> { assistantMessage };
                messages.AddRange(toolCallResults);

                return messages;
            }
            else if (message is Message msg)
            {
                if (msg.FunctionArguments is not null && msg.FunctionName is not null && msg.Content is not null)
                {
                    var assistantMessage = new ChatRequestAssistantMessage(msg.Content);
                    assistantMessage.FunctionCall = new FunctionCall(msg.FunctionName, msg.FunctionArguments);
                    var functionCallMessage = new ChatRequestFunctionMessage(msg.FunctionName, msg.Content);
                    return [assistantMessage, functionCallMessage];
                }
                else
                {
                    if (msg.Role == Role.Function)
                    {
                        return [new ChatRequestFunctionMessage(msg.FunctionName!, msg.Content!)];
                    }
                    else
                    {
                        var assistantMessage = new ChatRequestAssistantMessage(msg.Content!);
                        if (msg.FunctionName is not null && msg.FunctionArguments is not null)
                        {
                            assistantMessage.FunctionCall = new FunctionCall(msg.FunctionName, msg.FunctionArguments);
                        }

                        return [assistantMessage];
                    }
                }
            }
            else
            {
                throw new ArgumentException($"Unknown message type: {message.GetType()}");
            }
        }
    }

    public static IEnumerable<IMessage> ToAutoGenMessages(this IAgent agent, IEnumerable<IMessage<ChatRequestMessage>> openaiMessages)
    {
        throw new NotImplementedException();
    }

    public static IMessage ToAutoGenMessage(ChatRequestMessage openaiMessage, string? from = null)
    {
        throw new NotImplementedException();
    }
}
