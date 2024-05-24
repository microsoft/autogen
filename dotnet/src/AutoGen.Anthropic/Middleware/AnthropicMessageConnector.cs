// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
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
        var chatMessages = ProcessMessage(messages, agent);
        var response = await agent.GenerateReplyAsync(chatMessages, context.Options, cancellationToken);

        return response is IMessage<ChatCompletionResponse> chatMessage
            ? PostProcessMessage(chatMessage.Content, agent)
            : response;
    }

    public async IAsyncEnumerable<IStreamingMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var chatMessages = ProcessMessage(messages, agent);

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
        Delta? delta = chatMessage.Content.Delta;
        return delta != null && !string.IsNullOrEmpty(delta.Text)
            ? new TextMessageUpdate(role: Role.Assistant, delta.Text, from: agent.Name)
            : null;
    }

    private IEnumerable<IMessage> ProcessMessage(IEnumerable<IMessage> messages, IAgent agent)
    {
        return messages.SelectMany<IMessage, IMessage>(m =>
        {
            return m switch
            {
                TextMessage textMessage => ProcessTextMessage(textMessage, agent),
                _ => [m],
            };
        });
    }

    private IMessage PostProcessMessage(ChatCompletionResponse response, IAgent from)
    {
        if (response.Content is null)
            throw new ArgumentNullException(nameof(response.Content));

        if (response.Content.Count != 1)
            throw new NotSupportedException($"{nameof(response.Content)} != 1");

        return new TextMessage(Role.Assistant, ((TextContent)response.Content[0]).Text ?? string.Empty, from: from.Name);
    }

    private IEnumerable<IMessage<ChatMessage>> ProcessTextMessage(TextMessage textMessage, IAgent agent)
    {
        IEnumerable<ChatMessage> messages;

        if (textMessage.From == agent.Name)
        {
            messages = [new ChatMessage(
            "assistant", textMessage.Content)];
        }
        else if (textMessage.From is null)
        {
            if (textMessage.Role == Role.User)
            {
                messages = [new ChatMessage(
                "user", textMessage.Content)];
            }
            else if (textMessage.Role == Role.Assistant)
            {
                messages = [new ChatMessage(
                "assistant", textMessage.Content)];
            }
            else if (textMessage.Role == Role.System)
            {
                messages = [new ChatMessage(
                "system", textMessage.Content)];
            }
            else
            {
                throw new NotSupportedException($"Role {textMessage.Role} is not supported");
            }
        }
        else
        {
            // if from is not null, then the message is from user
            messages = [new ChatMessage(
            "user", textMessage.Content)];
        }

        return messages.Select(m => new MessageEnvelope<ChatMessage>(m, from: textMessage.From));
    }
}
