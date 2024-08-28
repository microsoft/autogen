// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.OpenAI;

namespace AutoGen.SemanticKernel;

/// <summary>
/// Semantic Kernel Agent
/// <listheader>Income message could be one of the following type:</listheader>
/// <list type="bullet">
/// <item><see cref="IMessage{T}"/> where T is <see cref="ChatMessageContent"/></item>
/// </list>
/// 
/// <listheader>Return message could be one of the following type:</listheader>
/// <list type="bullet">
/// <item><see cref="IMessage{T}"/> where T is <see cref="ChatMessageContent"/></item>
/// <item>(streaming) <see cref="IMessage{T}"/> where T is <see cref="StreamingChatMessageContent"/></item>
/// </list>
/// 
/// <para>To support more AutoGen built-in <see cref="IMessage"/>, register with <see cref="SemanticKernelChatMessageContentConnector"/>.</para>
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


    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null, CancellationToken cancellationToken = default)
    {
        var chatHistory = BuildChatHistory(messages);
        var option = BuildOption(options);
        var chatService = _kernel.GetRequiredService<IChatCompletionService>();

        var reply = await chatService.GetChatMessageContentsAsync(chatHistory, option, _kernel, cancellationToken);

        if (reply.Count > 1)
        {
            throw new InvalidOperationException("ResultsPerPrompt greater than 1 is not supported in this semantic kernel agent");
        }

        return new MessageEnvelope<ChatMessageContent>(reply.First(), from: this.Name);
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var chatHistory = BuildChatHistory(messages);
        var option = BuildOption(options);
        var chatService = _kernel.GetRequiredService<IChatCompletionService>();
        var response = chatService.GetStreamingChatMessageContentsAsync(chatHistory, option, _kernel, cancellationToken);

        await foreach (var content in response)
        {
            if (content.ChoiceIndex > 0)
            {
                throw new InvalidOperationException("Only one choice is supported in streaming response");
            }

            yield return new MessageEnvelope<StreamingChatMessageContent>(content, from: this.Name);
        }
    }

    private ChatHistory BuildChatHistory(IEnumerable<IMessage> messages)
    {
        var chatMessageContents = ProcessMessage(messages);
        // if there's no system message in chatMessageContents, add one to the beginning
        if (!chatMessageContents.Any(c => c.Role == AuthorRole.System))
        {
            chatMessageContents = new[] { new ChatMessageContent(AuthorRole.System, _systemMessage) }.Concat(chatMessageContents);
        }

        return new ChatHistory(chatMessageContents);
    }

    private PromptExecutionSettings BuildOption(GenerateReplyOptions? options)
    {
        return _settings ?? new OpenAIPromptExecutionSettings
        {
            Temperature = options?.Temperature ?? 0.7f,
            MaxTokens = options?.MaxToken ?? 1024,
            StopSequences = options?.StopSequence,
            ToolCallBehavior = ToolCallBehavior.AutoInvokeKernelFunctions,
        };
    }

    private IEnumerable<ChatMessageContent> ProcessMessage(IEnumerable<IMessage> messages)
    {
        return messages.Select(m => m switch
        {
            IMessage<ChatMessageContent> cmc => cmc.Content,
            _ => throw new ArgumentException("Invalid message type")
        });
    }
}
