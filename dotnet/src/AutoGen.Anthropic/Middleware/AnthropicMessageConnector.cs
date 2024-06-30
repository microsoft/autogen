// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicMessageConnector.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Runtime.CompilerServices;
using System.Text.Json.Nodes;
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
        var chatMessages = await ProcessMessageAsync(messages, agent);
        var response = await agent.GenerateReplyAsync(chatMessages, context.Options, cancellationToken);

        return response is IMessage<ChatCompletionResponse> chatMessage
            ? PostProcessMessage(chatMessage.Content, agent)
            : response;
    }

    public async IAsyncEnumerable<IStreamingMessage> InvokeAsync(MiddlewareContext context, IStreamingAgent agent,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var messages = context.Messages;
        var chatMessages = await ProcessMessageAsync(messages, agent);

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
        if (chatMessage.Content.Content is { Count: 1 } &&
            chatMessage.Content.Content[0] is ToolUseContent toolUseContent)
        {
            return new ToolCallMessage(
                toolUseContent.Name ??
                throw new InvalidOperationException($"Expected {nameof(toolUseContent.Name)} to be specified"),
                toolUseContent.Input?.ToString() ??
                throw new InvalidOperationException($"Expected {nameof(toolUseContent.Input)} to be specified"),
                from: agent.Name);
        }

        var delta = chatMessage.Content.Delta;
        return delta != null && !string.IsNullOrEmpty(delta.Text)
            ? new TextMessageUpdate(role: Role.Assistant, delta.Text, from: agent.Name)
            : null;
    }

    private async Task<IEnumerable<IMessage>> ProcessMessageAsync(IEnumerable<IMessage> messages, IAgent agent)
    {
        var processedMessages = new List<IMessage>();

        foreach (var message in messages)
        {
            var processedMessage = message switch
            {
                TextMessage textMessage => ProcessTextMessage(textMessage, agent),

                ImageMessage imageMessage =>
                    (MessageEnvelope<ChatMessage>[])[new MessageEnvelope<ChatMessage>(new ChatMessage("user",
                            new ContentBase[] { new ImageContent { Source = await ProcessImageSourceAsync(imageMessage) } }
                                .ToList()),
                        from: agent.Name)],

                MultiModalMessage multiModalMessage => await ProcessMultiModalMessageAsync(multiModalMessage, agent),

                ToolCallMessage toolCallMessage => ProcessToolCallMessage(toolCallMessage, agent),
                ToolCallResultMessage toolCallResultMessage => ProcessToolCallResultMessage(toolCallResultMessage),
                AggregateMessage<ToolCallMessage, ToolCallResultMessage> toolCallAggregateMessage => ProcessToolCallAggregateMessage(toolCallAggregateMessage, agent),
                _ => [message],
            };

            processedMessages.AddRange(processedMessage);
        }

        return processedMessages;
    }

    private IMessage PostProcessMessage(ChatCompletionResponse response, IAgent from)
    {
        if (response.Content is null)
        {
            throw new ArgumentNullException(nameof(response.Content));
        }

        // When expecting a tool call, sometimes the response will contain two messages, one chat and one tool.
        // The first message is typically a TextContent, of the LLM explaining what it is trying to do.
        // The second message contains the tool call.
        if (response.Content.Count > 1)
        {
            if (response.Content.Count == 2 && response.Content[0] is TextContent &&
                response.Content[1] is ToolUseContent toolUseContent)
            {
                return new ToolCallMessage(toolUseContent.Name ?? string.Empty,
                    toolUseContent.Input?.ToJsonString() ?? string.Empty,
                    from: from.Name);
            }

            throw new NotSupportedException($"Expected {nameof(response.Content)} to have one output");
        }

        var content = response.Content[0];
        switch (content)
        {
            case TextContent textContent:
                return new TextMessage(Role.Assistant, textContent.Text ?? string.Empty, from: from.Name);

            case ToolUseContent toolUseContent:
                return new ToolCallMessage(toolUseContent.Name ?? string.Empty,
                    toolUseContent.Input?.ToJsonString() ?? string.Empty,
                    from: from.Name);

            case ImageContent:
                throw new InvalidOperationException(
                    "Claude is an image understanding model only. It can interpret and analyze images, but it cannot generate, produce, edit, manipulate or create images");
            default:
                throw new ArgumentOutOfRangeException(nameof(content));
        }
    }

    private IEnumerable<IMessage<ChatMessage>> ProcessTextMessage(TextMessage textMessage, IAgent agent)
    {
        ChatMessage messages;

        if (textMessage.From == agent.Name)
        {
            messages = new ChatMessage(
                "assistant", textMessage.Content);
        }
        else if (textMessage.From is null)
        {
            if (textMessage.Role == Role.User)
            {
                messages = new ChatMessage(
                    "user", textMessage.Content);
            }
            else if (textMessage.Role == Role.Assistant)
            {
                messages = new ChatMessage(
                    "assistant", textMessage.Content);
            }
            else if (textMessage.Role == Role.System)
            {
                messages = new ChatMessage(
                    "system", textMessage.Content);
            }
            else
            {
                throw new NotSupportedException($"Role {textMessage.Role} is not supported");
            }
        }
        else
        {
            // if from is not null, then the message is from user
            messages = new ChatMessage(
                "user", textMessage.Content);
        }

        return [new MessageEnvelope<ChatMessage>(messages, from: textMessage.From)];
    }

    private async Task<IEnumerable<IMessage>> ProcessMultiModalMessageAsync(MultiModalMessage multiModalMessage, IAgent agent)
    {
        var content = new List<ContentBase>();
        foreach (var message in multiModalMessage.Content)
        {
            switch (message)
            {
                case TextMessage textMessage when textMessage.GetContent() is not null:
                    content.Add(new TextContent { Text = textMessage.GetContent() });
                    break;
                case ImageMessage imageMessage:
                    content.Add(new ImageContent() { Source = await ProcessImageSourceAsync(imageMessage) });
                    break;
            }
        }

        return [MessageEnvelope.Create(new ChatMessage("user", content), agent.Name)];
    }

    private async Task<ImageSource> ProcessImageSourceAsync(ImageMessage imageMessage)
    {
        if (imageMessage.Data != null)
        {
            return new ImageSource
            {
                MediaType = imageMessage.Data.MediaType,
                Data = Convert.ToBase64String(imageMessage.Data.ToArray())
            };
        }

        if (imageMessage.Url is null)
        {
            throw new InvalidOperationException("Invalid ImageMessage, the data or url must be provided");
        }

        var uri = new Uri(imageMessage.Url);
        using var client = new HttpClient();
        var response = client.GetAsync(uri).Result;
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"Failed to download the image from {uri}");
        }

        return new ImageSource
        {
            MediaType = "image/jpeg",
            Data = Convert.ToBase64String(await response.Content.ReadAsByteArrayAsync())
        };
    }

    private IEnumerable<IMessage> ProcessToolCallMessage(ToolCallMessage toolCallMessage, IAgent agent)
    {
        var chatMessage = new ChatMessage("assistant", new List<ContentBase>());
        foreach (var toolCall in toolCallMessage.ToolCalls)
        {
            chatMessage.AddContent(new ToolUseContent
            {
                Id = toolCall.ToolCallId,
                Name = toolCall.FunctionName,
                Input = JsonNode.Parse(toolCall.FunctionArguments)
            });
        }

        return [MessageEnvelope.Create(chatMessage, toolCallMessage.From)];
    }

    private IEnumerable<IMessage> ProcessToolCallResultMessage(ToolCallResultMessage toolCallResultMessage)
    {
        var chatMessage = new ChatMessage("user", new List<ContentBase>());
        foreach (var toolCall in toolCallResultMessage.ToolCalls)
        {
            chatMessage.AddContent(new ToolResultContent
            {
                Id = toolCall.ToolCallId ?? string.Empty,
                Content = toolCall.Result,
            });
        }

        return [MessageEnvelope.Create(chatMessage, toolCallResultMessage.From)];
    }

    private IEnumerable<IMessage> ProcessToolCallAggregateMessage(AggregateMessage<ToolCallMessage, ToolCallResultMessage> aggregateMessage, IAgent agent)
    {
        if (aggregateMessage.From is { } from && from != agent.Name)
        {
            var contents = aggregateMessage.Message2.ToolCalls.Select(t => t.Result);
            var messages = contents.Select(c =>
                new ChatMessage("assistant", c ?? throw new ArgumentNullException(nameof(c))));

            return messages.Select(m => new MessageEnvelope<ChatMessage>(m, from: from));
        }

        var toolCallMessage = ProcessToolCallMessage(aggregateMessage.Message1, agent);
        var toolCallResult = ProcessToolCallResultMessage(aggregateMessage.Message2);

        return toolCallMessage.Concat(toolCallResult);
    }
}
