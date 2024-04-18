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
                    TextMessage textMessage => ProcessTextMessage(textMessage, agent),
                    ToolCallMessage toolCallMessage when (toolCallMessage.From is null || toolCallMessage.From == agent.Name) => ProcessToolCallMessage(toolCallMessage, agent),
                    ToolCallResultMessage toolCallResultMessage => ProcessToolCallResultMessage(toolCallResultMessage, agent),
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

    private IEnumerable<IMessage<ChatMessage>> ProcessTextMessage(TextMessage textMessage, IAgent agent)
    {
        IEnumerable<ChatMessage> messages;
        // check if textMessage is system message
        if (textMessage.Role == Role.System)
        {
            messages = [new ChatMessage(ChatMessage.RoleEnum.System, textMessage.Content)];
        }

        // if this message is from agent iteself, then its role should be assistant
        if (textMessage.From == agent.Name)
        {
            messages = [new ChatMessage(ChatMessage.RoleEnum.Assistant, textMessage.Content)];
        }
        else if (textMessage.From is null)
        {
            // if from is null, then process the message based on the role
            if (textMessage.Role == Role.User)
            {
                messages = [new ChatMessage(ChatMessage.RoleEnum.User, textMessage.Content)];
            }
            else if (textMessage.Role == Role.Assistant)
            {
                messages = [new ChatMessage(ChatMessage.RoleEnum.Assistant, textMessage.Content)];
            }
            else
            {
                throw new NotSupportedException($"Role {textMessage.Role} is not supported");
            }
        }
        else
        {
            // if from is not null, then the message is from user
            messages = [new ChatMessage(ChatMessage.RoleEnum.User, textMessage.Content)];
        }

        return messages.Select(m => new MessageEnvelope<ChatMessage>(m, from: textMessage.From));
    }

    private IEnumerable<IMessage<ChatMessage>> ProcessToolCallResultMessage(ToolCallResultMessage toolCallResultMessage, IAgent agent)
    {
        var from = toolCallResultMessage.From;
        var messages = new List<ChatMessage>();
        foreach (var toolCall in toolCallResultMessage.ToolCalls)
        {
            if (toolCall.Result is null)
            {
                continue;
            }

            var message = new ChatMessage(ChatMessage.RoleEnum.Tool, content: toolCall.Result)
            {
                Name = toolCall.FunctionName,
            };

            messages.Add(message);
        }

        return messages.Select(m => new MessageEnvelope<ChatMessage>(m, from: toolCallResultMessage.From));
    }

    private IEnumerable<IMessage<ChatMessage>> ProcessToolCallMessage(ToolCallMessage toolCallMessage, IAgent agent)
    {
        IEnumerable<ChatMessage> messages;

        // the scenario is not support when tool call message is from another agent
        if (toolCallMessage.From is string from && from != agent.Name)
        {
            throw new NotSupportedException("Tool call message from another agent is not supported");
        }

        // convert tool call message to chat message
        var chatMessage = new ChatMessage(ChatMessage.RoleEnum.Assistant);
        chatMessage.ToolCalls = new List<FunctionContent>();
        foreach (var toolCall in toolCallMessage.ToolCalls)
        {
            var functionCall = new FunctionContent.FunctionCall(toolCall.FunctionName, toolCall.FunctionArguments);
            var functionContent = new FunctionContent(functionCall);
            chatMessage.ToolCalls.Add(functionContent);
        }

        messages = [chatMessage];

        return messages.Select(m => new MessageEnvelope<ChatMessage>(m, from: toolCallMessage.From));
    }
}
