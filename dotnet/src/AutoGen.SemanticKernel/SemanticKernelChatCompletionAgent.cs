// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelChatCompletionAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Agents;
using Microsoft.SemanticKernel.ChatCompletion;

namespace AutoGen.SemanticKernel;

public class SemanticKernelChatCompletionAgent : IAgent
{
    public string Name { get; }
    private readonly ChatCompletionAgent _chatCompletionAgent;
    private readonly string _systemMessage;

    public SemanticKernelChatCompletionAgent(ChatCompletionAgent chatCompletionAgent,
        string systemMessage = "You are a helpful AI assistant")
    {
        this.Name = chatCompletionAgent.Name ?? string.Empty;
        this._chatCompletionAgent = chatCompletionAgent;
        this._systemMessage = systemMessage;
    }

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        ChatMessageContent[] reply = await _chatCompletionAgent
            .InvokeAsync(BuildChatHistory(messages), cancellationToken)
            .ToArrayAsync(cancellationToken: cancellationToken);

        return reply.Length > 1
            ? throw new InvalidOperationException("ResultsPerPrompt greater than 1 is not supported in this semantic kernel agent")
            : new MessageEnvelope<ChatMessageContent>(reply[0], from: this.Name);
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

    private IEnumerable<ChatMessageContent> ProcessMessage(IEnumerable<IMessage> messages)
    {
        return messages.Select(m => m switch
        {
            IMessage<ChatMessageContent> cmc => cmc.Content,
            _ => throw new ArgumentException("Invalid message type")
        });
    }
}
