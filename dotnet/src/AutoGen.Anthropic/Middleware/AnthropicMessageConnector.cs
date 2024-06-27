// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Anthropic.DTO;
using AutoGen.Core;

namespace AutoGen.Anthropic.Middleware;

public class AnthropicMessageConnector : IStreamingMiddleware
{
    public string? Name => nameof(AnthropicMessageConnector);

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var chatMessages = await ProcessMessageAsync(messages, agent);
        var response = await agent.GenerateReplyAsync(chatMessages, context.Options, cancellationToken);

        return response is IMessage<ChatCompletionResponse> chatMessage
            ? PostProcessMessage(chatMessage.Content, agent)
            : response;
    }

    public async IAsyncEnumerable<IStreamingMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var chatMessages = await ProcessMessageAsync(messages, agent);

        await foreach (var reply in agent.GenerateStreamingReplyAsync(chatMessages, context.Options, cancellationToken))
        {
            if (reply is IStreamingMessage<ChatCompletionResponse> chatMessage)
            {
                var response = ProcessChatCompletionResponse(chatMessage, agent);
                if (response is not null)
                {
                    yield return response;
                }
            }
            else
            {
                yield return reply;
            }
        }
    }

    private IStreamingMessage? ProcessChatCompletionResponse(IStreamingMessage<ChatCompletionResponse> chatMessage,
        IStreamingAgent agent)
    {
        var delta = chatMessage.Content.Delta;
        return delta != null && !string.IsNullOrEmpty(delta.Text)
            ? new TextMessageUpdate(role: Role.Assistant, delta.Text, from: agent.Name)
            : null;
    }

    private async Task<IEnumerable<IMessage>> ProcessMessageAsync(IEnumerable<IMessage> messages, IAgent agent)
    {
        var processedMessages = new List<IMessage>();

        foreach (var message in messages)
        {
            var processedMessage = message switch
            {
                TextMessage textMessage => ProcessTextMessage(textMessage, agent),

                ImageMessage imageMessage =>
                    new MessageEnvelope<ChatMessage>(new ChatMessage("user",
                            new ContentBase[] { new ImageContent { Source = await ProcessImageSourceAsync(imageMessage) } }
                                .ToList()),
                        from: agent.Name),

                MultiModalMessage multiModalMessage => await ProcessMultiModalMessageAsync(multiModalMessage, agent),
                _ => message,
            };

            processedMessages.Add(processedMessage);
        }

        return processedMessages;
    }

    private IMessage PostProcessMessage(ChatCompletionResponse response, IAgent from)
    {
        if (response.Content is null)
        {
            throw new ArgumentNullException(nameof(response.Content));
        }

        if (response.Content.Count != 1)
        {
            throw new NotSupportedException($"{nameof(response.Content)} != 1");
        }

        return new TextMessage(Role.Assistant, ((TextContent)response.Content[0]).Text ?? string.Empty, from: from.Name);
    }

    private IMessage<ChatMessage> ProcessTextMessage(TextMessage textMessage, IAgent agent)
    {
        ChatMessage messages;

        if (textMessage.From == agent.Name)
        {
            messages = new ChatMessage(
                "assistant", textMessage.Content);
        }
        else if (textMessage.From is null)
        {
            if (textMessage.Role == Role.User)
            {
                messages = new ChatMessage(
                    "user", textMessage.Content);
            }
            else if (textMessage.Role == Role.Assistant)
            {
                messages = new ChatMessage(
                    "assistant", textMessage.Content);
            }
            else if (textMessage.Role == Role.System)
            {
                messages = new ChatMessage(
                    "system", textMessage.Content);
            }
            else
            {
                throw new NotSupportedException($"Role {textMessage.Role} is not supported");
            }
        }
        else
        {
            // if from is not null, then the message is from user
            messages = new ChatMessage(
                "user", textMessage.Content);
        }

        return new MessageEnvelope<ChatMessage>(messages, from: textMessage.From);
    }

    private async Task<IMessage> ProcessMultiModalMessageAsync(MultiModalMessage multiModalMessage, IAgent agent)
    {
        var content = new List<ContentBase>();
        foreach (var message in multiModalMessage.Content)
        {
            switch (message)
            {
                case TextMessage textMessage when textMessage.GetContent() is not null:
                    content.Add(new TextContent { Text = textMessage.GetContent() });
                    break;
                case ImageMessage imageMessage:
                    content.Add(new ImageContent() { Source = await ProcessImageSourceAsync(imageMessage) });
                    break;
            }
        }

        var chatMessage = new ChatMessage("user", content);
        return MessageEnvelope.Create(chatMessage, agent.Name);
    }

    private async Task<ImageSource> ProcessImageSourceAsync(ImageMessage imageMessage)
    {
        if (imageMessage.Data != null)
        {
            return new ImageSource
            {
                MediaType = imageMessage.Data.MediaType,
                Data = Convert.ToBase64String(imageMessage.Data.ToArray())
            };
        }

        if (imageMessage.Url is null)
        {
            throw new InvalidOperationException("Invalid ImageMessage, the data or url must be provided");
        }

        var uri = new Uri(imageMessage.Url);
        using var client = new HttpClient();
        var response = client.GetAsync(uri).Result;
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"Failed to download the image from {uri}");
        }

        return new ImageSource
        {
            MediaType = "image/jpeg",
            Data = Convert.ToBase64String(await response.Content.ReadAsByteArrayAsync())
        };
    }
}
