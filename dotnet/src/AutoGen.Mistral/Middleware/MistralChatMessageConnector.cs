// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralChatMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;

namespace AutoGen.Mistral;

public class MistralChatMessageConnector : IStreamingMiddleware, IMiddleware
{
    public string? Name => nameof(MistralChatMessageConnector);

    public Task<IAsyncEnumerable<IStreamingMessage>> InvokeAsync(MiddlewareContext context, IStreamingAgent agent, CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException();
    }

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var chatMessages = ProcessMessage(messages, agent);
        var response = await agent.GenerateReplyAsync(chatMessages, context.Options, cancellationToken);

        return PostProcessMessage(response);
    }

    private IEnumerable<IMessage> ProcessMessage(IEnumerable<IMessage> messages, IAgent agent)
    {
        return messages.SelectMany<IMessage, IMessage>(m =>
        {
            if (m is IMessage<ChatMessage> chatMessage)
            {
                return [MessageEnvelope.Create(chatMessage.Content, from: chatMessage.From)];
            }
            else
            {
                return m switch
                {
                    TextMessage textMessage => ProcessTextMessage(textMessage, agent).Select(c => MessageEnvelope.Create(c, from: textMessage.From)),
                    _ => [m],
                };
            }
        });
    }

    private IMessage PostProcessMessage(IMessage input)
    {
        return input switch
        {
            IMessage<ChatCompletionResponse> messageEnvelope => PostProcessMessage(messageEnvelope),
            _ => input,
        };
    }

    private IMessage PostProcessMessage(IMessage<ChatCompletionResponse> message)
    {
        var response = message.Content;
        if (response.Choices is null)
        {
            throw new ArgumentNullException("response.Choices");
        }

        if (response.Choices?.Count != 1)
        {
            throw new NotSupportedException("response.Choices.Count != 1");
        }

        var choice = response.Choices[0];
        var finishReason = choice.FinishReason ?? throw new ArgumentNullException("choice.FinishReason");

        if (finishReason == Choice.FinishReasonEnum.Stop || finishReason == Choice.FinishReasonEnum.Length)
        {
            return new TextMessage(Role.Assistant, choice.Message?.Content ?? throw new ArgumentNullException("choice.Message.Content"), from: message.From);
        }
        else if (finishReason == Choice.FinishReasonEnum.ToolCalls)
        {
            var functionContents = choice.Message?.ToolCalls ?? throw new ArgumentNullException("choice.Message.ToolCalls");
            var toolCalls = functionContents.Select(f => new ToolCall(f.Function.Name, f.Function.Arguments)).ToList();
            return new ToolCallMessage(toolCalls, from: message.From);
        }
        else
        {
            throw new NotSupportedException($"FinishReason {finishReason} is not supported");
        }
    }

    private IEnumerable<ChatMessage> ProcessTextMessage(TextMessage textMessage, IAgent agent)
    {
        // check if textMessage is system message
        if (textMessage.Role == Role.System)
        {
            return [new ChatMessage(ChatMessage.RoleEnum.System, textMessage.Content)];
        }

        // if this message is from agent iteself, then its role should be assistant
        if (textMessage.From == agent.Name)
        {
            return [new ChatMessage(ChatMessage.RoleEnum.Assistant, textMessage.Content)];
        }
        else if (textMessage.From is null)
        {
            // if from is null, then process the message based on the role
            if (textMessage.Role == Role.User)
            {
                return [new ChatMessage(ChatMessage.RoleEnum.User, textMessage.Content)];
            }
            else if (textMessage.Role == Role.Assistant)
            {
                return [new ChatMessage(ChatMessage.RoleEnum.Assistant, textMessage.Content)];
            }
            else
            {
                throw new NotSupportedException($"Role {textMessage.Role} is not supported");
            }
        }
        else
        {
            // if from is not null, then the message is from user
            return [new ChatMessage(ChatMessage.RoleEnum.User, textMessage.Content)];
        }
    }
}
