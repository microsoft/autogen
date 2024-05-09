// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Runtime.CompilerServices;
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
        switch (reply)
        {
            case IMessage<ChatResponse> messageEnvelope:
                Message? message = messageEnvelope.Content.Message;
                return new TextMessage(Role.Assistant, message != null ? message.Value : "EMPTY_CONTENT", messageEnvelope.From);
            default:
                throw new NotSupportedException();
        }
    }

    public async IAsyncEnumerable<IStreamingMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        await foreach (IStreamingMessage? update in agent.GenerateStreamingReplyAsync(context.Messages, context.Options, cancellationToken))
        {
            switch (update)
            {
                case IMessage<ChatResponse> complete:
                    {
                        string? textContent = complete.Content.Message?.Value;
                        yield return new TextMessage(Role.Assistant, textContent!, complete.From);
                        break;
                    }
                case IMessage<ChatResponseUpdate> updatedMessage:
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
