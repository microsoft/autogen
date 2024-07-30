// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatRequestMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI;

/// <summary>
/// This middleware converts the incoming <see cref="IMessage"/> to <see cref="IMessage{ChatRequestMessage}" /> where T is <see cref="ChatRequestMessage"/> before sending to agent. And converts the output <see cref="ChatResponseMessage"/> to <see cref="IMessage"/> after receiving from agent.
/// <para>Supported <see cref="IMessage"/> are</para>
/// <para>- <see cref="TextMessage"/></para> 
/// <para>- <see cref="ImageMessage"/></para> 
/// <para>- <see cref="MultiModalMessage"/></para>
/// <para>- <see cref="ToolCallMessage"/></para>
/// <para>- <see cref="ToolCallResultMessage"/></para>
/// <para>- <see cref="IMessage{ChatRequestMessage}"/> where T is <see cref="ChatRequestMessage"/></para>
/// <para>- <see cref="AggregateMessage{TMessage1, TMessage2}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/></para>
/// </summary>
public class OpenAIChatRequestMessageConnector : IMiddleware, IStreamingMiddleware
{
    private bool strictMode = false;

    /// <summary>
    /// Create a new instance of <see cref="OpenAIChatRequestMessageConnector"/>.
    /// </summary>
    /// <param name="strictMode">If true, <see cref="OpenAIChatRequestMessageConnector"/> will throw an <see cref="InvalidOperationException"/>
    /// When the message type is not supported. If false, it will ignore the unsupported message type.</param>
    public OpenAIChatRequestMessageConnector(bool strictMode = false)
    {
        this.strictMode = strictMode;
    }

    public string? Name => nameof(OpenAIChatRequestMessageConnector);

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        var chatMessages = ProcessIncomingMessages(agent, context.Messages);

        var reply = await agent.GenerateReplyAsync(chatMessages, context.Options, cancellationToken);

        return PostProcessMessage(reply);
    }

    public async IAsyncEnumerable<IMessage> InvokeAsync(
        MiddlewareContext context,
        IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var chatMessages = ProcessIncomingMessages(agent, context.Messages);
        var streamingReply = agent.GenerateStreamingReplyAsync(chatMessages, context.Options, cancellationToken);
        string? currentToolName = null;
        await foreach (var reply in streamingReply)
        {
            if (reply is IMessage<StreamingChatCompletionsUpdate> update)
            {
                if (update.Content.FunctionName is string functionName)
                {
                    currentToolName = functionName;
                }
                else if (update.Content.ToolCallUpdate is StreamingFunctionToolCallUpdate toolCallUpdate && toolCallUpdate.Name is string toolCallName)
                {
                    currentToolName = toolCallName;
                }
                var postProcessMessage = PostProcessStreamingMessage(update, currentToolName);
                if (postProcessMessage != null)
                {
                    yield return postProcessMessage;
                }
            }
            else
            {
                if (this.strictMode)
                {
                    throw new InvalidOperationException($"Invalid streaming message type {reply.GetType().Name}");
                }
                else
                {
                    yield return reply;
                }
            }
        }
    }

    public IMessage PostProcessMessage(IMessage message)
    {
        return message switch
        {
            IMessage<ChatResponseMessage> m => PostProcessChatResponseMessage(m.Content, m.From),
            IMessage<ChatCompletions> m => PostProcessChatCompletions(m),
            _ when strictMode is false => message,
            _ => throw new InvalidOperationException($"Invalid return message type {message.GetType().Name}"),
        };
    }

    public IMessage? PostProcessStreamingMessage(IMessage<StreamingChatCompletionsUpdate> update, string? currentToolName)
    {
        if (update.Content.ContentUpdate is string contentUpdate)
        {
            // text message
            return new TextMessageUpdate(Role.Assistant, contentUpdate, from: update.From);
        }
        else if (update.Content.FunctionName is string functionName)
        {
            return new ToolCallMessageUpdate(functionName, string.Empty, from: update.From);
        }
        else if (update.Content.FunctionArgumentsUpdate is string functionArgumentsUpdate && currentToolName is string)
        {
            return new ToolCallMessageUpdate(currentToolName, functionArgumentsUpdate, from: update.From);
        }
        else if (update.Content.ToolCallUpdate is StreamingFunctionToolCallUpdate tooCallUpdate && currentToolName is string)
        {
            return new ToolCallMessageUpdate(tooCallUpdate.Name ?? currentToolName, tooCallUpdate.ArgumentsUpdate, from: update.From);
        }
        else
        {
            return null;
        }
    }

    private IMessage PostProcessChatCompletions(IMessage<ChatCompletions> message)
    {
        // throw exception if prompt filter results is not null
        if (message.Content.Choices[0].FinishReason == CompletionsFinishReason.ContentFiltered)
        {
            throw new InvalidOperationException("The content is filtered because its potential risk. Please try another input.");
        }

        return PostProcessChatResponseMessage(message.Content.Choices[0].Message, message.From);
    }

    private IMessage PostProcessChatResponseMessage(ChatResponseMessage chatResponseMessage, string? from)
    {
        var textContent = chatResponseMessage.Content;
        if (chatResponseMessage.FunctionCall is FunctionCall functionCall)
        {
            return new ToolCallMessage(functionCall.Name, functionCall.Arguments, from)
            {
                Content = textContent,
            };
        }

        if (chatResponseMessage.ToolCalls.Where(tc => tc is ChatCompletionsFunctionToolCall).Any())
        {
            var functionToolCalls = chatResponseMessage.ToolCalls
                .Where(tc => tc is ChatCompletionsFunctionToolCall)
                .Select(tc => (ChatCompletionsFunctionToolCall)tc);

            var toolCalls = functionToolCalls.Select(tc => new ToolCall(tc.Name, tc.Arguments) { ToolCallId = tc.Id });

            return new ToolCallMessage(toolCalls, from)
            {
                Content = textContent,
            };
        }

        if (textContent is string content && !string.IsNullOrEmpty(content))
        {
            return new TextMessage(Role.Assistant, content, from);
        }

        throw new InvalidOperationException("Invalid ChatResponseMessage");
    }

    public IEnumerable<IMessage> ProcessIncomingMessages(IAgent agent, IEnumerable<IMessage> messages)
    {
        return messages.SelectMany<IMessage, IMessage>(m =>
        {
            if (m is IMessage<ChatRequestMessage> crm)
            {
                return [crm];
            }
            else
            {
                var chatRequestMessages = m switch
                {
                    TextMessage textMessage => ProcessTextMessage(agent, textMessage),
                    ImageMessage imageMessage when (imageMessage.From is null || imageMessage.From != agent.Name) => ProcessImageMessage(agent, imageMessage),
                    MultiModalMessage multiModalMessage when (multiModalMessage.From is null || multiModalMessage.From != agent.Name) => ProcessMultiModalMessage(agent, multiModalMessage),
                    ToolCallMessage toolCallMessage when (toolCallMessage.From is null || toolCallMessage.From == agent.Name) => ProcessToolCallMessage(agent, toolCallMessage),
                    ToolCallResultMessage toolCallResultMessage => ProcessToolCallResultMessage(toolCallResultMessage),
                    AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => ProcessFunctionCallMiddlewareMessage(agent, aggregateMessage),
#pragma warning disable CS0618 // deprecated
                    Message msg => ProcessMessage(agent, msg),
#pragma warning restore CS0618 // deprecated
                    _ when strictMode is false => [],
                    _ => throw new InvalidOperationException($"Invalid message type: {m.GetType().Name}"),
                };

                if (chatRequestMessages.Any())
                {
                    return chatRequestMessages.Select(cm => MessageEnvelope.Create(cm, m.From));
                }
                else
                {
                    return [m];
                }
            }
        });
    }

    [Obsolete("This method is deprecated, please use ProcessIncomingMessages(IAgent agent, IEnumerable<IMessage> messages) instead.")]
    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(Message message)
    {
        if (message.Role == Role.System)
        {
            return new[] { new ChatRequestSystemMessage(message.Content) };
        }
        else if (message.Content is string content && content is { Length: > 0 })
        {
            if (message.FunctionName is null)
            {
                return new[] { new ChatRequestAssistantMessage(message.Content) };
            }
            else
            {
                return new[] { new ChatRequestToolMessage(content, message.FunctionName) };
            }
        }
        else if (message.FunctionName is string functionName)
        {
            var msg = new ChatRequestAssistantMessage(content: null)
            {
                FunctionCall = new FunctionCall(functionName, message.FunctionArguments)
            };

            return new[]
            {
                msg,
            };
        }
        else
        {
            throw new InvalidOperationException("Invalid Message as message from self.");
        }
    }

    [Obsolete("This method is deprecated, please use ProcessIncomingMessages(IAgent agent, IEnumerable<IMessage> messages) instead.")]
    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(Message message)
    {
        if (message.Role == Role.System)
        {
            return [new ChatRequestSystemMessage(message.Content) { Name = message.From }];
        }
        else if (message.Content is string content && content is { Length: > 0 })
        {
            if (message.FunctionName is not null)
            {
                return new[] { new ChatRequestToolMessage(content, message.FunctionName) };
            }

            return [new ChatRequestUserMessage(message.Content) { Name = message.From }];
        }
        else if (message.FunctionName is string _)
        {
            return [new ChatRequestUserMessage("// Message type is not supported") { Name = message.From }];
        }
        else
        {
            throw new InvalidOperationException("Invalid Message as message from other.");
        }
    }

    private IEnumerable<ChatRequestMessage> ProcessTextMessage(IAgent agent, TextMessage message)
    {
        if (message.Role == Role.System)
        {
            return [new ChatRequestSystemMessage(message.Content) { Name = message.From }];
        }

        if (agent.Name == message.From)
        {
            return [new ChatRequestAssistantMessage(message.Content) { Name = agent.Name }];
        }
        else
        {
            return message.From switch
            {
                null when message.Role == Role.User => [new ChatRequestUserMessage(message.Content)],
                null when message.Role == Role.Assistant => [new ChatRequestAssistantMessage(message.Content)],
                null => throw new InvalidOperationException("Invalid Role"),
                _ => [new ChatRequestUserMessage(message.Content) { Name = message.From }]
            };
        }
    }

    private IEnumerable<ChatRequestMessage> ProcessImageMessage(IAgent agent, ImageMessage message)
    {
        if (agent.Name == message.From)
        {
            // image message from assistant is not supported
            throw new ArgumentException("ImageMessage is not supported when message.From is the same with agent");
        }

        var imageContentItem = this.CreateChatMessageImageContentItemFromImageMessage(message);
        return [new ChatRequestUserMessage([imageContentItem]) { Name = message.From }];
    }

    private IEnumerable<ChatRequestMessage> ProcessMultiModalMessage(IAgent agent, MultiModalMessage message)
    {
        if (agent.Name == message.From)
        {
            // image message from assistant is not supported
            throw new ArgumentException("MultiModalMessage is not supported when message.From is the same with agent");
        }

        IEnumerable<ChatMessageContentItem> items = message.Content.Select<IMessage, ChatMessageContentItem>(ci => ci switch
        {
            TextMessage text => new ChatMessageTextContentItem(text.Content),
            ImageMessage image => this.CreateChatMessageImageContentItemFromImageMessage(image),
            _ => throw new NotImplementedException(),
        });

        return [new ChatRequestUserMessage(items) { Name = message.From }];
    }

    private ChatMessageImageContentItem CreateChatMessageImageContentItemFromImageMessage(ImageMessage message)
    {
        return message.Data is null && message.Url is not null
            ? new ChatMessageImageContentItem(new Uri(message.Url))
            : new ChatMessageImageContentItem(message.Data, message.Data?.MediaType);
    }

    private IEnumerable<ChatRequestMessage> ProcessToolCallMessage(IAgent agent, ToolCallMessage message)
    {
        if (message.From is not null && message.From != agent.Name)
        {
            throw new ArgumentException("ToolCallMessage is not supported when message.From is not the same with agent");
        }

        var toolCall = message.ToolCalls.Select((tc, i) => new ChatCompletionsFunctionToolCall(tc.ToolCallId ?? $"{tc.FunctionName}_{i}", tc.FunctionName, tc.FunctionArguments));
        var textContent = message.GetContent() ?? string.Empty;
        var chatRequestMessage = new ChatRequestAssistantMessage(textContent) { Name = message.From };
        foreach (var tc in toolCall)
        {
            chatRequestMessage.ToolCalls.Add(tc);
        }

        return [chatRequestMessage];
    }

    private IEnumerable<ChatRequestMessage> ProcessToolCallResultMessage(ToolCallResultMessage message)
    {
        return message.ToolCalls
            .Where(tc => tc.Result is not null)
            .Select((tc, i) => new ChatRequestToolMessage(tc.Result, tc.ToolCallId ?? $"{tc.FunctionName}_{i}"));
    }

    [Obsolete("This method is deprecated, please use ProcessIncomingMessages(IAgent agent, IEnumerable<IMessage> messages) instead.")]
    private IEnumerable<ChatRequestMessage> ProcessMessage(IAgent agent, Message message)
    {
        if (message.From is not null && message.From != agent.Name)
        {
            return ProcessIncomingMessagesForOther(message);
        }
        else
        {
            return ProcessIncomingMessagesForSelf(message);
        }
    }

    private IEnumerable<ChatRequestMessage> ProcessFunctionCallMiddlewareMessage(IAgent agent, AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage)
    {
        if (aggregateMessage.From is not null && aggregateMessage.From != agent.Name)
        {
            // convert as user message
            var resultMessage = aggregateMessage.Message2;

            return resultMessage.ToolCalls.Select(tc => new ChatRequestUserMessage(tc.Result) { Name = aggregateMessage.From });
        }
        else
        {
            var toolCallMessage1 = aggregateMessage.Message1;
            var toolCallResultMessage = aggregateMessage.Message2;

            var assistantMessage = this.ProcessToolCallMessage(agent, toolCallMessage1);
            var toolCallResults = this.ProcessToolCallResultMessage(toolCallResultMessage);

            return assistantMessage.Concat(toolCallResults);
        }
    }
}
