// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Azure.AI.OpenAI;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.OpenAI;

namespace AutoGen.SemanticKernel;

/// <summary>
/// The agent that intergrade with the semantic kernel.
/// </summary>
public class SemanticKernelAgent : IStreamingAgent
{
    private readonly Kernel _kernel;
    private readonly string _systemMessage;
    private readonly PromptExecutionSettings? _settings;

    public SemanticKernelAgent(
        Kernel kernel,
        string name,
        string systemMessage = "You are a helpful AI assistant",
        PromptExecutionSettings? settings = null)
    {
        _kernel = kernel;
        this.Name = name;
        _systemMessage = systemMessage;
        _settings = settings;
    }
    public string Name { get; }


    public async Task<Message> GenerateReplyAsync(IEnumerable<Message> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        var chatMessageContents = ProcessMessage(messages);
        // if there's no system message in chatMessageContents, add one to the beginning
        if (!chatMessageContents.Any(c => c.Role == AuthorRole.System))
        {
            chatMessageContents = new[] { new ChatMessageContent(AuthorRole.System, _systemMessage) }.Concat(chatMessageContents);
        }

        var chatHistory = new ChatHistory(chatMessageContents);
        var option = _settings ?? new OpenAIPromptExecutionSettings
        {
            Temperature = options?.Temperature ?? 0.7f,
            MaxTokens = options?.MaxToken ?? 1024,
            StopSequences = options?.StopSequence,
        };

        var chatService = _kernel.GetRequiredService<IChatCompletionService>();

        var reply = await chatService.GetChatMessageContentsAsync(chatHistory, option, _kernel, cancellationToken);

        if (reply.Count() == 1)
        {
            // might be a plain text return or a function call return
            var msg = reply.First();
            if (msg is OpenAIChatMessageContent oaiContent)
            {
                if (oaiContent.Content is string content)
                {
                    return new Message(Role.Assistant, content, this.Name);
                }
                else if (oaiContent.ToolCalls is { Count: 1 } && oaiContent.ToolCalls.First() is ChatCompletionsFunctionToolCall toolCall)
                {
                    return new Message(Role.Assistant, content: null, this.Name)
                    {
                        FunctionName = toolCall.Name,
                        FunctionArguments = toolCall.Arguments,
                    };
                }
                else
                {
                    // parallel function call is not supported
                    throw new InvalidOperationException("Unsupported return type, only plain text and function call are supported.");
                }
            }
            else
            {
                throw new InvalidOperationException("Unsupported return type");
            }
        }
        else
        {
            throw new InvalidOperationException("Unsupported return type, multiple messages are not supported.");
        }
    }

    public async Task<IAsyncEnumerable<IMessage>> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var chatMessageContents = ProcessMessage(messages);
        // if there's no system message in chatMessageContents, add one to the beginning
        if (!chatMessageContents.Any(c => c.Role == AuthorRole.System))
        {
            chatMessageContents = new[] { new ChatMessageContent(AuthorRole.System, _systemMessage) }.Concat(chatMessageContents);
        }

        var chatHistory = new ChatHistory(chatMessageContents);
        var option = _settings ?? new OpenAIPromptExecutionSettings
        {
            Temperature = options?.Temperature ?? 0.7f,
            MaxTokens = options?.MaxToken ?? 1024,
            StopSequences = options?.StopSequence,
        };

        var chatService = _kernel.GetRequiredService<IChatCompletionService>();
        var response = chatService.GetStreamingChatMessageContentsAsync(chatHistory, option, _kernel, cancellationToken);

        return ProcessMessage(response);
    }

    private async IAsyncEnumerable<IMessage> ProcessMessage(IAsyncEnumerable<StreamingChatMessageContent> response)
    {
        string? text = null;
        await foreach (var content in response)
        {
            if (content is OpenAIStreamingChatMessageContent oaiStreamingChatContent && oaiStreamingChatContent.Content is string chunk)
            {
                text += chunk;
                yield return new Message(Role.Assistant, text, this.Name);
            }
            else
            {
                throw new InvalidOperationException("Unsupported return type");
            }
        }

        if (text is not null)
        {
            yield return new Message(Role.Assistant, text, this.Name);
        }
    }

    private IEnumerable<ChatMessageContent> ProcessMessage(IEnumerable<IMessage> messages)
    {
        return messages.SelectMany(m =>
        {
            if (m is IMessage<ChatMessageContent> chatMessageContent)
            {
                return [chatMessageContent.Content];
            }
            if (m.From == this.Name)
            {
                return ProcessMessageForSelf(m);
            }
            else
            {
                return ProcessMessageForOthers(m);
            }
        });
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForSelf(IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => ProcessMessageForSelf(textMessage),
            MultiModalMessage multiModalMessage => ProcessMessageForSelf(multiModalMessage),
            Message m => ProcessMessageForSelf(m),
            _ => throw new System.NotImplementedException(),
        };
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(IMessage message)
    {
        return message switch
        {
            TextMessage textMessage => ProcessMessageForOthers(textMessage),
            MultiModalMessage multiModalMessage => ProcessMessageForOthers(multiModalMessage),
            Message m => ProcessMessageForOthers(m),
            _ => throw new System.NotImplementedException(),
        };
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForSelf(TextMessage message)
    {
        if (message.Role == Role.System)
        {
            return [new ChatMessageContent(AuthorRole.System, message.Content)];
        }
        else
        {
            return [new ChatMessageContent(AuthorRole.Assistant, message.Content)];
        }
    }


    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(TextMessage message)
    {
        if (message.Role == Role.System)
        {
            return [new ChatMessageContent(AuthorRole.System, message.Content)];
        }
        else
        {
            return [new ChatMessageContent(AuthorRole.User, message.Content)];
        }
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForSelf(MultiModalMessage message)
    {
        throw new System.InvalidOperationException("MultiModalMessage is not supported in the semantic kernel if it's from self.");
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(MultiModalMessage message)
    {
        var collections = new ChatMessageContentItemCollection();
        foreach (var item in message.Content)
        {
            if (item is TextMessage textContent)
            {
                collections.Add(new TextContent(textContent.Content));
            }
            else if (item is ImageMessage imageContent)
            {
                collections.Add(new ImageContent(new Uri(imageContent.Url)));
            }
            else
            {
                throw new InvalidOperationException($"Unsupported message type: {item.GetType().Name}");
            }
        }
        return [new ChatMessageContent(AuthorRole.User, collections)];
    }


    private IEnumerable<ChatMessageContent> ProcessMessageForSelf(Message message)
    {
        if (message.Role == Role.System)
        {
            return [new ChatMessageContent(AuthorRole.System, message.Content)];
        }
        else if (message.Content is string && message.FunctionName is null && message.FunctionArguments is null)
        {
            return [new ChatMessageContent(AuthorRole.Assistant, message.Content)];
        }
        else if (message.Content is null && message.FunctionName is not null && message.FunctionArguments is not null)
        {
            throw new System.InvalidOperationException("Function call is not supported in the semantic kernel if it's from self.");
        }
        else
        {
            throw new System.InvalidOperationException("Unsupported message type");
        }
    }

    private IEnumerable<ChatMessageContent> ProcessMessageForOthers(Message message)
    {
        if (message.Role == Role.System)
        {
            return [new ChatMessageContent(AuthorRole.System, message.Content)];
        }
        else if (message.Content is string && message.FunctionName is null && message.FunctionArguments is null)
        {
            return [new ChatMessageContent(AuthorRole.User, message.Content)];
        }
        else if (message.Content is null && message.FunctionName is not null && message.FunctionArguments is not null)
        {
            throw new System.InvalidOperationException("Function call is not supported in the semantic kernel if it's from others.");
        }
        else
        {
            throw new System.InvalidOperationException("Unsupported message type");
        }
    }
}
