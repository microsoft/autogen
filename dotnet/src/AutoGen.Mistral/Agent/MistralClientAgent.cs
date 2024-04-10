// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralClientAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core;

namespace AutoGen.Mistral;

public class MistralClientAgent : IStreamingAgent
{
    private readonly MistralClient _client;
    private readonly string _systemMessage;
    private readonly string _model;
    private readonly int? _randomSeed;
    private readonly bool _jsonOutput = false;
    public MistralClientAgent(
        MistralClient client,
        string name,
        string model,
        string systemMessage = "You are a helpful AI assistant",
        int? randomSeed = null,
        bool jsonOutput = false)
    {
        _client = client;
        Name = name;
        _systemMessage = systemMessage;
        _model = model;
        _randomSeed = randomSeed;
        _jsonOutput = jsonOutput;
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var request = BuildChatRequest(messages, options);
        var response = await _client.CreateChatCompletionsAsync(request);

        return new MessageEnvelope<ChatCompletionResponse>(response, from: this.Name);
    }

    public async Task<IAsyncEnumerable<IStreamingMessage>> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var request = BuildChatRequest(messages, options);
        var response = _client.StreamingChatCompletionsAsync(request);

        return ProcessMessage(response);
    }

    private async IAsyncEnumerable<IMessage> ProcessMessage(IAsyncEnumerable<ChatCompletionResponse> response)
    {
        await foreach (var content in response)
        {
            yield return new MessageEnvelope<ChatCompletionResponse>(content, from: this.Name);
        }
    }

    private ChatCompletionRequest BuildChatRequest(IEnumerable<IMessage> messages, GenerateReplyOptions? options)
    {
        var chatHistory = BuildChatHistory(messages);
        var chatRequest = new ChatCompletionRequest(model: _model, messages: chatHistory.ToList(), temperature: options?.Temperature, randomSeed: _randomSeed)
        {
            MaxTokens = options?.MaxToken,
            ResponseFormat = _jsonOutput ? new ResponseFormat() { ResponseFormatType = "json_object" } : null,
        };

        return chatRequest;
    }

    private IEnumerable<ChatMessage> BuildChatHistory(IEnumerable<IMessage> messages)
    {
        var history = messages.Select(m => m switch
        {
            IMessage<ChatMessage> chatMessage => chatMessage.Content,
            _ => throw new ArgumentException("Invalid message type")
        });

        // if there's no system message in the history, add one to the beginning
        if (!history.Any(m => m.Role == ChatMessage.RoleEnum.System))
        {
            history = new[] { new ChatMessage(ChatMessage.RoleEnum.System, _systemMessage) }.Concat(history);
        }

        return history;
    }
}
