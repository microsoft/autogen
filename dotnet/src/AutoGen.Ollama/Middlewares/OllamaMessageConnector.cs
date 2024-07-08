// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;

namespace AutoGen.Ollama;

public class OllamaMessageConnector : IStreamingMiddleware
{
    public string Name => nameof(OllamaMessageConnector);

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent,
        CancellationToken cancellationToken = default)
    {
        var messages = ProcessMessage(context.Messages, agent);
        IMessage reply = await agent.GenerateReplyAsync(messages, context.Options, cancellationToken);

        return reply switch
        {
            IMessage<ChatResponse> messageEnvelope when messageEnvelope.Content.Message?.Value is string content => new TextMessage(Role.Assistant, content, messageEnvelope.From),
            IMessage<ChatResponse> messageEnvelope when messageEnvelope.Content.Message?.Value is null => throw new InvalidOperationException("Message content is null"),
            _ => reply
        };
    }

    public async IAsyncEnumerable<IMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var messages = ProcessMessage(context.Messages, agent);
        var chunks = new List<ChatResponseUpdate>();
        await foreach (var update in agent.GenerateStreamingReplyAsync(messages, context.Options, cancellationToken))
        {
            if (update is IMessage<ChatResponseUpdate> chatResponseUpdate)
            {
                var response = chatResponseUpdate.Content switch
                {
                    _ when chatResponseUpdate.Content.Message?.Value is string content => new TextMessageUpdate(Role.Assistant, content, chatResponseUpdate.From),
                    _ => null,
                };

                if (response != null)
                {
                    chunks.Add(chatResponseUpdate.Content);
                    yield return response;
                }
            }
            else
            {
                yield return update;
            }
        }

        if (chunks.Count == 0)
        {
            yield break;
        }

        // if the chunks are not empty, aggregate them into a single message
        var messageContent = string.Join(string.Empty, chunks.Select(c => c.Message?.Value));
        var message = new TextMessage(Role.Assistant, messageContent, agent.Name);

        yield return message;
    }

    private IEnumerable<IMessage> ProcessMessage(IEnumerable<IMessage> messages, IAgent agent)
    {
        return messages.SelectMany(m =>
        {
            if (m is IMessage<Message> messageEnvelope)
            {
                return [m];
            }
            else
            {
                return m switch
                {
                    TextMessage textMessage => ProcessTextMessage(textMessage, agent),
                    ImageMessage imageMessage => ProcessImageMessage(imageMessage, agent),
                    MultiModalMessage multiModalMessage => ProcessMultiModalMessage(multiModalMessage, agent),
                    _ => [m],
                };
            }
        });
    }

    private IEnumerable<IMessage> ProcessMultiModalMessage(MultiModalMessage multiModalMessage, IAgent agent)
    {
        var textMessages = multiModalMessage.Content.Where(m => m is TextMessage textMessage && textMessage.GetContent() is not null);
        var imageMessages = multiModalMessage.Content.Where(m => m is ImageMessage);

        // aggregate the text messages into one message
        // by concatenating the content using newline
        var textContent = string.Join("\n", textMessages.Select(m => ((TextMessage)m).Content));

        // collect all the images
        var images = imageMessages.SelectMany(m => ProcessImageMessage((ImageMessage)m, agent)
                    .SelectMany(m => (m as IMessage<Message>)?.Content.Images));

        var message = new Message()
        {
            Role = "user",
            Value = textContent,
            Images = images.ToList(),
        };

        return [MessageEnvelope.Create(message, agent.Name)];
    }

    private IEnumerable<IMessage> ProcessImageMessage(ImageMessage imageMessage, IAgent agent)
    {
        byte[]? data = imageMessage.Data?.ToArray();
        if (data is null)
        {
            if (imageMessage.Url is null)
            {
                throw new InvalidOperationException("Invalid ImageMessage, the data or url must be provided");
            }

            var uri = new Uri(imageMessage.Url);
            // download the image from the URL
            using var client = new HttpClient();
            var response = client.GetAsync(uri).Result;
            if (!response.IsSuccessStatusCode)
            {
                throw new HttpRequestException($"Failed to download the image from {uri}");
            }

            data = response.Content.ReadAsByteArrayAsync().Result;
        }

        var base64Image = Convert.ToBase64String(data);
        var message = imageMessage.From switch
        {
            null when imageMessage.Role == Role.User => new Message { Role = "user", Images = [base64Image] },
            null => throw new InvalidOperationException("Invalid Role, the role must be user"),
            _ when imageMessage.From != agent.Name => new Message { Role = "user", Images = [base64Image] },
            _ => throw new InvalidOperationException("The from field must be null or the agent name"),
        };

        return [MessageEnvelope.Create(message, agent.Name)];
    }

    private IEnumerable<IMessage> ProcessTextMessage(TextMessage textMessage, IAgent agent)
    {
        if (textMessage.Role == Role.System)
        {
            var message = new Message
            {
                Role = "system",
                Value = textMessage.Content
            };

            return [MessageEnvelope.Create(message, agent.Name)];
        }
        else if (textMessage.From == agent.Name)
        {
            var message = new Message
            {
                Role = "assistant",
                Value = textMessage.Content
            };

            return [MessageEnvelope.Create(message, agent.Name)];
        }
        else
        {
            var message = textMessage.From switch
            {
                null when textMessage.Role == Role.User => new Message { Role = "user", Value = textMessage.Content },
                null when textMessage.Role == Role.Assistant => new Message { Role = "assistant", Value = textMessage.Content },
                null => throw new InvalidOperationException("Invalid Role"),
                _ when textMessage.From != agent.Name => new Message { Role = "user", Value = textMessage.Content },
                _ => throw new InvalidOperationException("The from field must be null or the agent name"),
            };

            return [MessageEnvelope.Create(message, agent.Name)];
        }
    }
}
