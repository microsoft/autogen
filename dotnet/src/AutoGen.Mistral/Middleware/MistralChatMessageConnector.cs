// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralChatMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;

namespace AutoGen.Mistral;

public class MistralChatMessageConnector : IStreamingMiddleware, IMiddleware
{
    public string? Name => nameof(MistralChatMessageConnector);

    public async IAsyncEnumerable<IMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var chatMessages = ProcessMessage(messages, agent);
        var chunks = new List<ChatCompletionResponse>();
        await foreach (var reply in agent.GenerateStreamingReplyAsync(chatMessages, context.Options, cancellationToken))
        {
            if (reply is IMessage<ChatCompletionResponse> chatMessage)
            {
                chunks.Add(chatMessage.Content);
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

        // if chunks is not empty, then return the aggregate message as the last message
        // this is to meet the requirement of streaming call api
        // where the last message should be the same result of non-streaming call api
        if (chunks.Count == 0)
        {
            yield break;
        }

        var lastResponse = chunks.Last() ?? throw new ArgumentNullException("chunks.Last()");
        var finalResponse = chunks.First() ?? throw new ArgumentNullException("chunks.First()");
        if (lastResponse.Choices!.First().FinishReason == Choice.FinishReasonEnum.ToolCalls)
        {
            // process as tool call message
            foreach (var response in chunks)
            {
                if (finalResponse.Choices!.First().Message is null)
                {
                    finalResponse.Choices!.First().Message = response.Choices!.First().Delta;
                    if (finalResponse.Choices!.First().Message!.ToolCalls is null)
                    {
                        finalResponse.Choices!.First().Message!.ToolCalls = new List<FunctionContent>();
                    }
                }

                if (response.Choices!.First().Delta!.ToolCalls is not null)
                {
                    finalResponse.Choices!.First().Message!.ToolCalls!.AddRange(response.Choices!.First().Delta!.ToolCalls!);
                }

                finalResponse.Choices!.First().FinishReason = response.Choices!.First().FinishReason;

                // the usage information will be included in the last message
                if (response.Usage is not null)
                {
                    finalResponse.Usage = response.Usage;
                }
            }
        }
        else
        {
            // process as plain text message
            foreach (var response in chunks)
            {
                if (finalResponse.Choices!.First().Message is null)
                {
                    finalResponse.Choices!.First().Message = response.Choices!.First().Delta;
                }

                finalResponse.Choices!.First().Message!.Content += response.Choices!.First().Delta!.Content;
                finalResponse.Choices!.First().FinishReason = response.Choices!.First().FinishReason;
                // the usage information will be included in the last message
                if (response.Usage is not null)
                {
                    finalResponse.Usage = response.Usage;
                }
            }
        }

        yield return PostProcessMessage(finalResponse, agent);
    }

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var chatMessages = ProcessMessage(messages, agent);
        var response = await agent.GenerateReplyAsync(chatMessages, context.Options, cancellationToken);

        if (response is IMessage<ChatCompletionResponse> chatMessage)
        {
            return PostProcessMessage(chatMessage.Content, agent);
        }
        else
        {
            return response;
        }
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
                    AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => ProcessFunctionCallMiddlewareMessage(aggregateMessage, agent), // message type support for functioncall middleware
                    _ => [m],
                };
            }
        });
    }

    private IMessage PostProcessMessage(ChatCompletionResponse response, IAgent from)
    {
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
            return new TextMessage(Role.Assistant, choice.Message?.Content ?? throw new ArgumentNullException("choice.Message.Content"), from: from.Name);
        }
        else if (finishReason == Choice.FinishReasonEnum.ToolCalls)
        {
            var functionContents = choice.Message?.ToolCalls ?? throw new ArgumentNullException("choice.Message.ToolCalls");
            var toolCalls = functionContents.Select(f => new ToolCall(f.Function.Name, f.Function.Arguments) { ToolCallId = f.Id }).ToList();
            return new ToolCallMessage(toolCalls, from: from.Name);
        }
        else
        {
            throw new NotSupportedException($"FinishReason {finishReason} is not supported");
        }
    }

    private IMessage? ProcessChatCompletionResponse(IMessage<ChatCompletionResponse> message, IAgent agent)
    {
        var response = message.Content;
        if (response.VarObject != "chat.completion.chunk")
        {
            throw new NotSupportedException($"VarObject {response.VarObject} is not supported");
        }
        if (response.Choices is null)
        {
            throw new ArgumentNullException("response.Choices");
        }

        if (response.Choices?.Count != 1)
        {
            throw new NotSupportedException("response.Choices.Count != 1");
        }

        var choice = response.Choices[0];
        var delta = choice.Delta;

        // process text message if delta.content is not null
        if (delta?.Content is string content)
        {
            return new TextMessageUpdate(role: Role.Assistant, content, from: agent.Name);
        }
        else if (delta?.ToolCalls is var toolCalls && toolCalls is { Count: 1 })
        {
            var toolCall = toolCalls[0];
            var functionContent = toolCall.Function;

            return new ToolCallMessageUpdate(functionContent.Name, functionContent.Arguments, from: agent.Name);
        }
        else
        {
            return null;
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
        else if (textMessage.From == agent.Name)
        {
            // if this message is from agent iteself, then its role should be assistant
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

    private IEnumerable<IMessage<ChatMessage>> ProcessToolCallResultMessage(ToolCallResultMessage toolCallResultMessage, IAgent _)
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
                ToolCallId = toolCall.ToolCallId,
            };

            messages.Add(message);
        }

        return messages.Select(m => new MessageEnvelope<ChatMessage>(m, from: toolCallResultMessage.From));
    }

    /// <summary>
    /// Process the aggregate message from function call middleware. If the message is from another agent, this message will be interpreted as an ordinary plain <see cref="TextMessage"/>.
    /// If the message is from the same agent or the from field is empty, this message will be expanded to the tool call message and tool call result message.
    /// </summary>
    /// <param name="aggregateMessage"></param>
    /// <param name="agent"></param>
    /// <returns></returns>
    /// <exception cref="NotSupportedException"></exception>
    private IEnumerable<IMessage<ChatMessage>> ProcessFunctionCallMiddlewareMessage(AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage, IAgent agent)
    {
        if (aggregateMessage.From is string from && from != agent.Name)
        {
            // if the message is from another agent, then interpret it as a plain text message
            // where the content of the plain text message is the content of the tool call result message
            var contents = aggregateMessage.Message2.ToolCalls.Select(t => t.Result);
            var messages = contents.Select(c => new ChatMessage(ChatMessage.RoleEnum.Assistant, c));

            return messages.Select(m => new MessageEnvelope<ChatMessage>(m, from: from));
        }

        // if the message is from the same agent or the from field is empty, then expand the message to tool call message and tool call result message
        var toolCallMessage = aggregateMessage.Message1;
        var toolCallResultMessage = aggregateMessage.Message2;

        return this.ProcessToolCallMessage(toolCallMessage, agent).Concat(this.ProcessToolCallResultMessage(toolCallResultMessage, agent));
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
        for (var i = 0; i < toolCallMessage.ToolCalls.Count; i++)
        {
            var toolCall = toolCallMessage.ToolCalls[i];
            var toolCallId = toolCall.ToolCallId ?? $"{toolCall.FunctionName}_{i}";
            var functionCall = new FunctionContent.FunctionCall(toolCall.FunctionName, toolCall.FunctionArguments);
            var functionContent = new FunctionContent(toolCallId, functionCall);
            chatMessage.ToolCalls.Add(functionContent);
        }

        messages = [chatMessage];

        return messages.Select(m => new MessageEnvelope<ChatMessage>(m, from: toolCallMessage.From));
    }
}
