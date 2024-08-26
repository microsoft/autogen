// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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
            .InvokeAsync(BuildChatHistory(messages), cancellationToken)
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
