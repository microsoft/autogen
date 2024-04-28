// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;

namespace Autogen.Ollama;

public class OllamaMessageConnector : IMiddleware, IStreamingMiddleware
{
    public string Name => nameof(OllamaMessageConnector);

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent,
        CancellationToken cancellationToken = default)
    {
        IEnumerable<IMessage> messages = context.Messages;
        IMessage reply = await agent.GenerateReplyAsync(messages, context.Options, cancellationToken);
        return PostProcessMessage(reply, context);
    }

    public async Task<IAsyncEnumerable<IStreamingMessage>> InvokeAsync(MiddlewareContext context, IStreamingAgent agent,
        CancellationToken cancellationToken = default)
    {
        IAsyncEnumerable<IStreamingMessage> stream = await agent.GenerateStreamingReplyAsync(context.Messages, context.Options, cancellationToken);
        return TransformStream(stream);

        async IAsyncEnumerable<IStreamingMessage> TransformStream(IAsyncEnumerable<IStreamingMessage> originalStream)
        {
            await foreach (IStreamingMessage? update in originalStream.WithCancellation(cancellationToken))
            {
                switch (update)
                {
                    case IMessage<CompleteChatMessage> complete:
                        {
                            string? textContent = complete.Content.Message?.Value;
                            yield return new TextMessage(Role.Assistant, textContent!, complete.From);
                            break;
                        }
                    case IMessage<ChatMessage> updatedMessage:
                        {
                            string? textContent = updatedMessage.Content.Message?.Value;
                            yield return new TextMessageUpdate(Role.Assistant, textContent, updatedMessage.From);
                            break;
                        }
                    default:
                        throw new InvalidOperationException("Message type not supported.");
                }
            }
        }
    }
    private static TextMessage PostProcessMessage(IMessage input, MiddlewareContext context)
    {
        switch (input)
        {
            case IMessage<CompleteChatMessage> messageEnvelope:
                Message? message = messageEnvelope.Content.Message;
                return new TextMessage(Role.Assistant, message != null ? message.Value : "EMPTY_CONTENT", messageEnvelope.From);
            default:
                throw new NotSupportedException();
        }
    }
}
