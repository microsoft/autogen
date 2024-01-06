// Copyright (c) Microsoft Corporation. All rights reserved.
// MessageExtension.cs

using System;
using System.Collections.Generic;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI.Extension;

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
}
