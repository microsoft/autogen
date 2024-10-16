// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatRequestMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using OpenAI.Chat;

namespace AutoGen.OpenAI;

/// <summary>
/// This middleware converts the incoming <see cref="IMessage"/> to <see cref="IMessage{ChatMessage}" /> where T is <see cref="ChatMessage"/> before sending to agent. And converts the output <see cref="ChatCompletion"/> to <see cref="IMessage"/> after receiving from agent.
/// <para>Supported <see cref="IMessage"/> are</para>
/// <para>- <see cref="TextMessage"/></para> 
/// <para>- <see cref="ImageMessage"/></para> 
/// <para>- <see cref="MultiModalMessage"/></para>
/// <para>- <see cref="ToolCallMessage"/></para>
/// <para>- <see cref="ToolCallResultMessage"/></para>
/// <para>- <see cref="IMessage{ChatMessage}"/> where T is <see cref="ChatMessage"/></para>
/// <para>- <see cref="AggregateMessage{TMessage1, TMessage2}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/></para>
/// </summary>
public class OpenAIChatRequestMessageConnector : IMiddleware, IStreamingMiddleware
{
    private bool strictMode;

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
        var chunks = new List<StreamingChatCompletionUpdate>();

        // only streaming the text content
        await foreach (var reply in streamingReply)
        {
            if (reply is IMessage<StreamingChatCompletionUpdate> update)
            {
                if (update.Content.ContentUpdate.Count == 1 && update.Content.ContentUpdate[0].Kind == ChatMessageContentPartKind.Text)
                {
                    yield return new TextMessageUpdate(Role.Assistant, update.Content.ContentUpdate[0].Text, from: update.From);
                }

                chunks.Add(update.Content);
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

        // process the tool call
        var streamingChatToolCallUpdates = chunks.Where(c => c.ToolCallUpdates.Count > 0)
                                                .SelectMany(c => c.ToolCallUpdates)
                                                .ToList();

        // collect all text parts
        var textParts = chunks.SelectMany(c => c.ContentUpdate)
            .Where(c => c.Kind == ChatMessageContentPartKind.Text)
            .Select(c => c.Text)
            .ToList();

        // combine the tool call and function call into one ToolCallMessages
        var text = string.Join(string.Empty, textParts);
        var toolCalls = new List<ToolCall>();
        var currentToolName = string.Empty;
        var currentToolArguments = string.Empty;
        var currentToolId = string.Empty;
        int? currentIndex = null;
        foreach (var toolCall in streamingChatToolCallUpdates)
        {
            if (currentIndex is null)
            {
                currentIndex = toolCall.Index;
            }

            if (toolCall.Index == currentIndex)
            {
                currentToolName += toolCall.FunctionName;
                currentToolArguments += toolCall.FunctionArgumentsUpdate;
                currentToolId += toolCall.ToolCallId;

                yield return new ToolCallMessageUpdate(currentToolName, currentToolArguments, from: agent.Name);
            }
            else
            {
                toolCalls.Add(new ToolCall(currentToolName, currentToolArguments) { ToolCallId = currentToolId });
                currentToolName = toolCall.FunctionName;
                currentToolArguments = toolCall.FunctionArgumentsUpdate.ToString();
                currentToolId = toolCall.ToolCallId;
                currentIndex = toolCall.Index;

                yield return new ToolCallMessageUpdate(currentToolName, currentToolArguments, from: agent.Name);
            }
        }

        if (string.IsNullOrEmpty(currentToolName) is false)
        {
            toolCalls.Add(new ToolCall(currentToolName, currentToolArguments) { ToolCallId = currentToolId });
        }

        if (toolCalls.Any())
        {
            yield return new ToolCallMessage(toolCalls, from: agent.Name)
            {
                Content = text,
            };
        }
    }

    public IMessage PostProcessMessage(IMessage message)
    {
        return message switch
        {
            IMessage<ChatCompletion> m => PostProcessChatCompletions(m),
            _ when strictMode is false => message,
            _ => throw new InvalidOperationException($"Invalid return message type {message.GetType().Name}"),
        };
    }

    private IMessage PostProcessChatCompletions(IMessage<ChatCompletion> message)
    {
        // throw exception if prompt filter results is not null
        if (message.Content.FinishReason == ChatFinishReason.ContentFilter)
        {
            throw new InvalidOperationException("The content is filtered because its potential risk. Please try another input.");
        }

        // throw exception is there is more than on choice
        if (message.Content.Content.Count > 1)
        {
            throw new InvalidOperationException("The content has more than one choice. Please try another input.");
        }

        return PostProcessChatResponseMessage(message.Content, message.From);
    }

    private IMessage PostProcessChatResponseMessage(ChatCompletion chatCompletion, string? from)
    {
        // throw exception if prompt filter results is not null
        if (chatCompletion.FinishReason == ChatFinishReason.ContentFilter)
        {
            throw new InvalidOperationException("The content is filtered because its potential risk. Please try another input.");
        }

        // throw exception is there is more than on choice
        if (chatCompletion.Content.Count > 1)
        {
            throw new InvalidOperationException("The content has more than one choice. Please try another input.");
        }
        var textContent = chatCompletion.Content is { Count: > 0 } ? chatCompletion.Content[0] : null;

        // if tool calls is not empty, return ToolCallMessage
        if (chatCompletion.ToolCalls is { Count: > 0 })
        {
            var toolCalls = chatCompletion.ToolCalls.Select(tc => new ToolCall(tc.FunctionName, tc.FunctionArguments.ToString()) { ToolCallId = tc.Id });
            return new ToolCallMessage(toolCalls, from)
            {
                Content = textContent?.Kind switch
                {
                    _ when textContent?.Kind == ChatMessageContentPartKind.Text => textContent.Text,
                    _ => null,
                },
            };
        }

        // if the content is text, return TextMessage
        if (textContent?.Kind == ChatMessageContentPartKind.Text)
        {
            return new TextMessage(Role.Assistant, textContent.Text, from);
        }

        throw new InvalidOperationException("Invalid ChatResponseMessage");
    }

    public IEnumerable<IMessage> ProcessIncomingMessages(IAgent agent, IEnumerable<IMessage> messages)
    {
        return messages.SelectMany<IMessage, IMessage>(m =>
        {
            if (m is IMessage<ChatMessage> crm)
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

    private IEnumerable<ChatMessage> ProcessTextMessage(IAgent agent, TextMessage message)
    {
        if (message.Role == Role.System)
        {
            return [new SystemChatMessage(message.Content) { ParticipantName = message.From }];
        }

        if (agent.Name == message.From)
        {
            return [new AssistantChatMessage(message.Content) { ParticipantName = agent.Name }];
        }
        else
        {
            return message.From switch
            {
                null when message.Role == Role.User => [new UserChatMessage(message.Content)],
                null when message.Role == Role.Assistant => [new AssistantChatMessage(message.Content)],
                null => throw new InvalidOperationException("Invalid Role"),
                _ => [new UserChatMessage(message.Content) { ParticipantName = message.From }]
            };
        }
    }

    private IEnumerable<ChatMessage> ProcessImageMessage(IAgent agent, ImageMessage message)
    {
        if (agent.Name == message.From)
        {
            // image message from assistant is not supported
            throw new ArgumentException("ImageMessage is not supported when message.From is the same with agent");
        }

        var imageContentItem = this.CreateChatMessageImageContentItemFromImageMessage(message);
        return [new UserChatMessage([imageContentItem]) { ParticipantName = message.From }];
    }

    private IEnumerable<ChatMessage> ProcessMultiModalMessage(IAgent agent, MultiModalMessage message)
    {
        if (agent.Name == message.From)
        {
            // image message from assistant is not supported
            throw new ArgumentException("MultiModalMessage is not supported when message.From is the same with agent");
        }

        IEnumerable<ChatMessageContentPart> items = message.Content.Select<IMessage, ChatMessageContentPart>(ci => ci switch
        {
            TextMessage text => ChatMessageContentPart.CreateTextPart(text.Content),
            ImageMessage image => this.CreateChatMessageImageContentItemFromImageMessage(image),
            _ => throw new NotImplementedException(),
        });

        return [new UserChatMessage(items) { ParticipantName = message.From }];
    }

    private ChatMessageContentPart CreateChatMessageImageContentItemFromImageMessage(ImageMessage message)
    {
        return message.Data is null && message.Url is not null
            ? ChatMessageContentPart.CreateImagePart(new Uri(message.Url))
            : ChatMessageContentPart.CreateImagePart(message.Data, message.Data?.MediaType);
    }

    private IEnumerable<ChatMessage> ProcessToolCallMessage(IAgent agent, ToolCallMessage message)
    {
        if (message.From is not null && message.From != agent.Name)
        {
            throw new ArgumentException("ToolCallMessage is not supported when message.From is not the same with agent");
        }

        var toolCallParts = message.ToolCalls.Select((tc, i) => ChatToolCall.CreateFunctionToolCall(tc.ToolCallId ?? $"{tc.FunctionName}_{i}", tc.FunctionName, BinaryData.FromString(tc.FunctionArguments)));
        var textContent = message.GetContent() ?? null;

        // Don't set participant name for assistant when it is tool call
        // fix https://github.com/microsoft/autogen/issues/3437
        AssistantChatMessage chatRequestMessage;

        if (string.IsNullOrEmpty(textContent) is true)
        {
            chatRequestMessage = new AssistantChatMessage(toolCallParts);
        }
        else
        {
            chatRequestMessage = new AssistantChatMessage(textContent);

            foreach (var toolCallPart in toolCallParts)
            {
                chatRequestMessage.ToolCalls.Add(toolCallPart);
            }
        }

        return [chatRequestMessage];
    }

    private IEnumerable<ChatMessage> ProcessToolCallResultMessage(ToolCallResultMessage message)
    {
        return message.ToolCalls
            .Where(tc => tc.Result is not null)
            .Select((tc, i) => new ToolChatMessage(tc.ToolCallId ?? $"{tc.FunctionName}_{i}", tc.Result));
    }

    private IEnumerable<ChatMessage> ProcessFunctionCallMiddlewareMessage(IAgent agent, AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage)
    {
        if (aggregateMessage.From is not null && aggregateMessage.From != agent.Name)
        {
            // convert as user message
            var resultMessage = aggregateMessage.Message2;

            return resultMessage.ToolCalls.Select(tc => new UserChatMessage(tc.Result) { ParticipantName = aggregateMessage.From });
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
