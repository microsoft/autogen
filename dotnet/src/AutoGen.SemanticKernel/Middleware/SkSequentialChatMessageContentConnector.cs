// Copyright (c) Microsoft Corporation. All rights reserved.
// SkSequentialChatMessageContentConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;

namespace AutoGen.SemanticKernel;

public class SkSequentialChatMessageContentConnector : IMiddleware
{
    public string? Name => nameof(SemanticKernelChatMessageContentConnector);

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent,
        CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;

        var chatMessageContents = ProcessMessage(messages, agent)
            .Select(m => new MessageEnvelope<ChatMessageContent>(m));
        var reply = await agent.GenerateReplyAsync(chatMessageContents, context.Options, cancellationToken);

        return PostProcessMessage(reply);
    }

    protected IEnumerable<ChatMessageContent> ProcessMessage(IEnumerable<IMessage> messages, IAgent agent)
    {
        return messages.SelectMany(m =>
        {
            if (m is IMessage<ChatMessageContent> chatMessageContent)
            {
                return [chatMessageContent.Content];
            }

            if (m.From == agent.Name)
            {
                return ProcessMessageForSelf(m);
            }
            else
            {
                return ProcessMessageForOthers(m);
            }
        });
    }

    protected IMessage PostProcessMessage(IMessage input)
    {
        return input switch
        {
            IMessage<ChatMessageContent> messageEnvelope => PostProcessMessage(messageEnvelope),
            _ => input,
        };
    }

    private IMessage PostProcessMessage(IMessage<ChatMessageContent> messageEnvelope)
    {
        var chatMessageContent = messageEnvelope.Content;
        var items = chatMessageContent.Items.Select<KernelContent, IMessage>(i => i switch
        {
            TextContent txt => new TextMessage(Role.Assistant, txt.Text!, messageEnvelope.From),
            ImageContent img when img.Uri is Uri uri => new ImageMessage(Role.Assistant, uri.ToString(), from: messageEnvelope.From),
            ImageContent img when img.Data is ReadOnlyMemory<byte> data => new ImageMessage(Role.Assistant, BinaryData.FromBytes(data), from: messageEnvelope.From),
            _ => throw new InvalidOperationException("Unsupported content type"),
        });

        if (items.Count() == 1)
        {
            return items.First();
        }
        else
        {
            return new MultiModalMessage(Role.Assistant, items, from: messageEnvelope.From);
        }
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForSelf(IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => ProcessMessageForSelf(textMessage),
            MultiModalMessage multiModalMessage => ProcessMessageForSelf(multiModalMessage),
            Message m => ProcessMessageForSelf(m),
            _ => throw new System.NotImplementedException(),
        };
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => ProcessMessageForOthers(textMessage),
            MultiModalMessage multiModalMessage => ProcessMessageForOthers(multiModalMessage),
            ImageMessage imageMessage => ProcessMessageForOthers(imageMessage),
            Message m => ProcessMessageForOthers(m),
            _ => throw new InvalidOperationException("unsupported message type, only support TextMessage, ImageMessage, MultiModalMessage and Message."),
        };
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(TextMessage message)
    {
        if (message.Role == Role.System)
        {
            return [new ChatMessageContent(AuthorRole.System, message.Content)];
        }
        else
        {
            return [new ChatMessageContent(AuthorRole.User, message.Content)];
        }
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(MultiModalMessage message)
    {
        var collections = new ChatMessageContentItemCollection();
        foreach (var item in message.Content)
        {
            if (item is TextMessage textContent)
            {
                collections.Add(new TextContent(textContent.Content));
            }
            else if (item is ImageMessage imageContent)
            {
                collections.Add(new ImageContent(new Uri(imageContent.Url ?? imageContent.BuildDataUri())));
            }
            else
            {
                throw new InvalidOperationException($"Unsupported message type: {item.GetType().Name}");
            }
        }
        return [new ChatMessageContent(AuthorRole.User, collections)];
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(ImageMessage message)
    {
        var collectionItems = new ChatMessageContentItemCollection();
        collectionItems.Add(new ImageContent(new Uri(message.Url ?? message.BuildDataUri())));
        return [new ChatMessageContent(AuthorRole.User, collectionItems)];
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(Message message)
    {
        if (message.Role == Role.System)
        {
            return [new ChatMessageContent(AuthorRole.System, message.Content)];
        }
        else if (message.Content is string && message.FunctionName is null && message.FunctionArguments is null)
        {
            return [new ChatMessageContent(AuthorRole.User, message.Content)];
        }
        else if (message.Content is null && message.FunctionName is not null && message.FunctionArguments is not null)
        {
            throw new InvalidOperationException("Function call is not supported in the semantic kernel if it's from others.");
        }
        else
        {
            throw new InvalidOperationException("Unsupported message type");
        }
    }
}
