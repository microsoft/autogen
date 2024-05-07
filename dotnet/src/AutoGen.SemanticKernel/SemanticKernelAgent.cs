// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Agents;

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
    public string Name { get; }

    private readonly ChatCompletionAgent _chatCompletionAgent;
    private readonly string _systemMessage;

    public SemanticKernelAgent(ChatCompletionAgent chatCompletionAgent, string name,
        string systemMessage = "You are a helpful AI assistant")
    {
        this.Name = name;
        this._chatCompletionAgent = chatCompletionAgent;
        this._systemMessage = systemMessage;
    }

    [Obsolete($"This constructor will be removed. Use SemanticKernelAgent constructor with ChatCompletionAgent instead of Kernel")]
    public SemanticKernelAgent(Kernel kernel,
        string name,
        string systemMessage = "You are a helpful AI assistant",
        PromptExecutionSettings? settings = null)
    {
        this.Name = name;
        this._chatCompletionAgent = new ChatCompletionAgent();
        this._systemMessage = systemMessage;
    }

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        ChatMessageContent[] reply = await _chatCompletionAgent
            .InvokeAsync(BuildChatHistory(messages), cancellationToken)
            .ToArrayAsync(cancellationToken: cancellationToken);

        return reply.Length > 1
            ? throw new InvalidOperationException(
                "ResultsPerPrompt greater than 1 is not supported in this semantic kernel agent")
            : new MessageEnvelope<ChatMessageContent>(reply[0], from: this.Name);
    }

    public async Task<IAsyncEnumerable<IStreamingMessage>> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var chatHistory = BuildChatHistory(messages);
        var response = _chatCompletionAgent.InvokeAsync(chatHistory, cancellationToken);

        return ProcessMessage(response);
    }

    private ChatHistory BuildChatHistory(IEnumerable<IMessage> messages)
    {
        var chatMessageContents = ProcessMessage(messages);
        // if there's no system message in chatMessageContents, add one to the beginning
        if (!chatMessageContents.Any(c => c.Role == AuthorRole.System))
        {
            chatMessageContents =
                new[] { new ChatMessageContent(AuthorRole.System, _systemMessage) }.Concat(chatMessageContents);
        }

        return new ChatHistory(chatMessageContents);
    }


    private async IAsyncEnumerable<IMessage> ProcessMessage(IAsyncEnumerable<ChatMessageContent> response)
    {
        await foreach (var content in response)
        {
            yield return new MessageEnvelope<ChatMessageContent>(content, from: this.Name);
        }
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
