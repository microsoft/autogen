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
/// <para>- <see cref="Message"/></para>
/// <para>- <see cref="IMessage{ChatRequestMessage}"/> where T is <see cref="ChatRequestMessage"/></para>
/// <para>- <see cref="AggregateMessage{TMessage1, TMessage2}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/></para>
/// </summary>
public class OpenAIChatRequestMessageConnector : IMiddleware, IStreamingMiddleware
{
    private bool strictMode = false;

    public OpenAIChatRequestMessageConnector(bool strictMode = false)
    {
        this.strictMode = strictMode;
    }

    public string? Name => nameof(OpenAIChatRequestMessageConnector);

    public async Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        var chatMessages = ProcessIncomingMessages(agent, context.Messages)
            .Select(m => new MessageEnvelope<ChatRequestMessage>(m));

        var reply = await agent.GenerateReplyAsync(chatMessages, context.Options, cancellationToken);

        return PostProcessMessage(reply);
    }

    public async IAsyncEnumerable<IStreamingMessage> InvokeAsync(
        MiddlewareContext context,
        IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var chatMessages = ProcessIncomingMessages(agent, context.Messages)
            .Select(m => new MessageEnvelope<ChatRequestMessage>(m));
        var streamingReply = agent.GenerateStreamingReplyAsync(chatMessages, context.Options, cancellationToken);
        string? currentToolName = null;
        await foreach (var reply in streamingReply)
        {
            if (reply is IStreamingMessage<StreamingChatCompletionsUpdate> update)
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
                yield return reply;
            }
        }
    }

    public IMessage PostProcessMessage(IMessage message)
    {
        return message switch
        {
            TextMessage => message,
            ImageMessage => message,
            MultiModalMessage => message,
            ToolCallMessage => message,
            ToolCallResultMessage => message,
            Message => message,
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> => message,
            IMessage<ChatResponseMessage> m => PostProcessMessage(m),
            IMessage<ChatCompletions> m => PostProcessMessage(m),
            _ => throw new InvalidOperationException("The type of message is not supported. Must be one of TextMessage, ImageMessage, MultiModalMessage, ToolCallMessage, ToolCallResultMessage, Message, IMessage<ChatRequestMessage>, AggregateMessage<ToolCallMessage, ToolCallResultMessage>"),
        };
    }

    public IStreamingMessage? PostProcessStreamingMessage(IStreamingMessage<StreamingChatCompletionsUpdate> update, string? currentToolName)
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

    private IMessage PostProcessMessage(IMessage<ChatResponseMessage> message)
    {
        return PostProcessMessage(message.Content, message.From);
    }

    private IMessage PostProcessMessage(IMessage<ChatCompletions> message)
    {
        // throw exception if prompt filter results is not null
        if (message.Content.Choices[0].FinishReason == CompletionsFinishReason.ContentFiltered)
        {
            throw new InvalidOperationException("The content is filtered because its potential risk. Please try another input.");
        }

        return PostProcessMessage(message.Content.Choices[0].Message, message.From);
    }

    private IMessage PostProcessMessage(ChatResponseMessage chatResponseMessage, string? from)
    {
        if (chatResponseMessage.Content is string content)
        {
            return new TextMessage(Role.Assistant, content, from);
        }

        if (chatResponseMessage.FunctionCall is FunctionCall functionCall)
        {
            return new ToolCallMessage(functionCall.Name, functionCall.Arguments, from);
        }

        if (chatResponseMessage.ToolCalls.Where(tc => tc is ChatCompletionsFunctionToolCall).Any())
        {
            var functionToolCalls = chatResponseMessage.ToolCalls
                .Where(tc => tc is ChatCompletionsFunctionToolCall)
                .Select(tc => (ChatCompletionsFunctionToolCall)tc);

            var toolCalls = functionToolCalls.Select(tc => new ToolCall(tc.Name, tc.Arguments));

            return new ToolCallMessage(toolCalls, from);
        }

        throw new InvalidOperationException("Invalid ChatResponseMessage");
    }

    public IEnumerable<ChatRequestMessage> ProcessIncomingMessages(IAgent agent, IEnumerable<IMessage> messages)
    {
        return messages.SelectMany(m =>
        {
            if (m.From == null)
            {
                return ProcessIncomingMessagesWithEmptyFrom(m);
            }
            else if (m.From == agent.Name)
            {
                return ProcessIncomingMessagesForSelf(m);
            }
            else
            {
                return ProcessIncomingMessagesForOther(m);
            }
        });
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => ProcessIncomingMessagesForSelf(textMessage),
            ImageMessage imageMessage => ProcessIncomingMessagesForSelf(imageMessage),
            MultiModalMessage multiModalMessage => ProcessIncomingMessagesForSelf(multiModalMessage),
            ToolCallMessage toolCallMessage => ProcessIncomingMessagesForSelf(toolCallMessage),
            ToolCallResultMessage toolCallResultMessage => ProcessIncomingMessagesForSelf(toolCallResultMessage),
            Message msg => ProcessIncomingMessagesForSelf(msg),
            IMessage<ChatRequestMessage> crm => ProcessIncomingMessagesForSelf(crm),
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => ProcessIncomingMessagesForSelf(aggregateMessage),
            _ => throw new NotImplementedException(),
        };
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => ProcessIncomingMessagesWithEmptyFrom(textMessage),
            ImageMessage imageMessage => ProcessIncomingMessagesWithEmptyFrom(imageMessage),
            MultiModalMessage multiModalMessage => ProcessIncomingMessagesWithEmptyFrom(multiModalMessage),
            ToolCallMessage toolCallMessage => ProcessIncomingMessagesWithEmptyFrom(toolCallMessage),
            ToolCallResultMessage toolCallResultMessage => ProcessIncomingMessagesWithEmptyFrom(toolCallResultMessage),
            Message msg => ProcessIncomingMessagesWithEmptyFrom(msg),
            IMessage<ChatRequestMessage> crm => ProcessIncomingMessagesWithEmptyFrom(crm),
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => ProcessIncomingMessagesWithEmptyFrom(aggregateMessage),
            _ => throw new NotImplementedException(),
        };
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => ProcessIncomingMessagesForOther(textMessage),
            ImageMessage imageMessage => ProcessIncomingMessagesForOther(imageMessage),
            MultiModalMessage multiModalMessage => ProcessIncomingMessagesForOther(multiModalMessage),
            ToolCallMessage toolCallMessage => ProcessIncomingMessagesForOther(toolCallMessage),
            ToolCallResultMessage toolCallResultMessage => ProcessIncomingMessagesForOther(toolCallResultMessage),
            Message msg => ProcessIncomingMessagesForOther(msg),
            IMessage<ChatRequestMessage> crm => ProcessIncomingMessagesForOther(crm),
            AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage => ProcessIncomingMessagesForOther(aggregateMessage),
            _ => throw new NotImplementedException(),
        };
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(TextMessage message)
    {
        if (message.Role == Role.System)
        {
            return new[] { new ChatRequestSystemMessage(message.Content) };
        }
        else
        {
            return new[] { new ChatRequestAssistantMessage(message.Content) };
        }
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(ImageMessage _)
    {
        return [new ChatRequestAssistantMessage("// Image Message is not supported")];
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(MultiModalMessage _)
    {
        return [new ChatRequestAssistantMessage("// MultiModal Message is not supported")];
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(ToolCallMessage message)
    {
        var toolCall = message.ToolCalls.Select(tc => new ChatCompletionsFunctionToolCall(tc.FunctionName, tc.FunctionName, tc.FunctionArguments));
        var chatRequestMessage = new ChatRequestAssistantMessage(string.Empty);
        foreach (var tc in toolCall)
        {
            chatRequestMessage.ToolCalls.Add(tc);
        }

        return new[] { chatRequestMessage };
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(ToolCallResultMessage message)
    {
        return message.ToolCalls.Select(tc => new ChatRequestToolMessage(tc.Result, tc.FunctionName));
    }

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

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(IMessage<ChatRequestMessage> message)
    {
        return new[] { message.Content };
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForSelf(AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage)
    {
        var toolCallMessage1 = aggregateMessage.Message1;
        var toolCallResultMessage = aggregateMessage.Message2;

        var assistantMessage = new ChatRequestAssistantMessage(string.Empty);
        var toolCalls = toolCallMessage1.ToolCalls.Select(tc => new ChatCompletionsFunctionToolCall(tc.FunctionName, tc.FunctionName, tc.FunctionArguments));
        foreach (var tc in toolCalls)
        {
            assistantMessage.ToolCalls.Add(tc);
        }

        var toolCallResults = toolCallResultMessage.ToolCalls.Select(tc => new ChatRequestToolMessage(tc.Result, tc.FunctionName));

        // return assistantMessage and tool call result messages
        var messages = new List<ChatRequestMessage> { assistantMessage };
        messages.AddRange(toolCallResults);

        return messages;
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(TextMessage message)
    {
        if (message.Role == Role.System)
        {
            return new[] { new ChatRequestSystemMessage(message.Content) };
        }
        else
        {
            return new[] { new ChatRequestUserMessage(message.Content) };
        }
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(ImageMessage message)
    {
        return new[] { new ChatRequestUserMessage([
            new ChatMessageImageContentItem(new Uri(message.Url ?? message.BuildDataUri())),
            ])};
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(MultiModalMessage message)
    {
        IEnumerable<ChatMessageContentItem> items = message.Content.Select<IMessage, ChatMessageContentItem>(ci => ci switch
        {
            TextMessage text => new ChatMessageTextContentItem(text.Content),
            ImageMessage image => new ChatMessageImageContentItem(new Uri(image.Url ?? image.BuildDataUri())),
            _ => throw new NotImplementedException(),
        });

        return new[] { new ChatRequestUserMessage(items) };
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(ToolCallMessage msg)
    {
        throw new ArgumentException("ToolCallMessage is not supported when message.From is not the same with agent");
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(ToolCallResultMessage message)
    {
        return message.ToolCalls.Select(tc => new ChatRequestToolMessage(tc.Result, tc.FunctionName));
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(Message message)
    {
        if (message.Role == Role.System)
        {
            return new[] { new ChatRequestSystemMessage(message.Content) };
        }
        else if (message.Content is string content && content is { Length: > 0 })
        {
            if (message.FunctionName is not null)
            {
                return new[] { new ChatRequestToolMessage(content, message.FunctionName) };
            }

            return new[] { new ChatRequestUserMessage(message.Content) };
        }
        else if (message.FunctionName is string _)
        {
            return new[]
            {
                new ChatRequestUserMessage("// Message type is not supported"),
            };
        }
        else
        {
            throw new InvalidOperationException("Invalid Message as message from other.");
        }
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(IMessage<ChatRequestMessage> message)
    {
        return new[] { message.Content };
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesForOther(AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage)
    {
        // convert as user message
        var resultMessage = aggregateMessage.Message2;

        return resultMessage.ToolCalls.Select(tc => new ChatRequestUserMessage(tc.Result));
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(TextMessage message)
    {
        return ProcessIncomingMessagesForOther(message);
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(ImageMessage message)
    {
        return ProcessIncomingMessagesForOther(message);
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(MultiModalMessage message)
    {
        return ProcessIncomingMessagesForOther(message);
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(ToolCallMessage message)
    {
        return ProcessIncomingMessagesForSelf(message);
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(ToolCallResultMessage message)
    {
        return ProcessIncomingMessagesForOther(message);
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(Message message)
    {
        return ProcessIncomingMessagesForOther(message);
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(IMessage<ChatRequestMessage> message)
    {
        return new[] { message.Content };
    }

    private IEnumerable<ChatRequestMessage> ProcessIncomingMessagesWithEmptyFrom(AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage)
    {
        return ProcessIncomingMessagesForOther(aggregateMessage);
    }
}
