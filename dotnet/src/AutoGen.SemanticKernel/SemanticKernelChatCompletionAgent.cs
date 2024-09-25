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

    public SemanticKernelChatCompletionAgent(ChatCompletionAgent chatCompletionAgent)
    {
        this.Name = chatCompletionAgent.Name ?? throw new ArgumentNullException(nameof(chatCompletionAgent.Name));
        this._chatCompletionAgent = chatCompletionAgent;
    }

    public async Task<IMessage> GenerateReplyAsync(IEnumerable<IMessage> messages, GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        ChatMessageContent[] reply = await _chatCompletionAgent
            .InvokeAsync(BuildChatHistory(messages), cancellationToken: cancellationToken)
            .ToArrayAsync(cancellationToken: cancellationToken);

        return reply.Length > 1
            ? throw new InvalidOperationException("ResultsPerPrompt greater than 1 is not supported in this semantic kernel agent")
            : new MessageEnvelope<ChatMessageContent>(reply[0], from: this.Name);
    }

    private ChatHistory BuildChatHistory(IEnumerable<IMessage> messages)
    {
        return new ChatHistory(ProcessMessage(messages));
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
