// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIClientAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI;

/// <summary>
/// OpenAI client agent. This agent is a thin wrapper around <see cref="OpenAIClient"/> to provide a simple interface for chat completions.
/// To better work with other agents, it's recommended to use <see cref="GPTAgent"/> which supports more message types and have a better compatibility with other agents.
/// <para><see cref="OpenAIClientAgent" /> supports the following message types:</para>
/// <list type="bullet">
/// <item>
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="ChatRequestMessage"/>: chat request message.
/// </item>
/// </list>
/// <para><see cref="OpenAIClientAgent" /> returns the following message types:</para>
/// <list type="bullet">
/// <item>
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="ChatResponseMessage"/>: chat response message.
/// </item>
/// </list>
/// </summary>
public class OpenAIClientAgent : IStreamingAgent
{
    private readonly OpenAIClient openAIClient;
    private readonly string modelName;
    private readonly float _temperature;
    private readonly int _maxTokens = 1024;
    private readonly IEnumerable<FunctionDefinition>? _functions;
    private readonly string _systemMessage;

    public OpenAIClientAgent(
        OpenAIClient openAIClient,
        string name,
        string systemMessage,
        string modelName,
        float temperature = 0.7f,
        int maxTokens = 1024,
        IEnumerable<FunctionDefinition>? functions = null)
    {
        this.openAIClient = openAIClient;
        this.modelName = modelName;
        this.Name = name;
        _temperature = temperature;
        _maxTokens = maxTokens;
        _functions = functions;
        _systemMessage = systemMessage;
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var settings = this.CreateChatCompletionsOptions(options, messages);
        var reply = await this.openAIClient.GetChatCompletionsAsync(settings, cancellationToken);

        return new MessageEnvelope<ChatResponseMessage>(reply.Value.Choices.First().Message, from: this.Name);
    }

    public Task<IAsyncEnumerable<IMessage>> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException();
    }

    private ChatCompletionsOptions CreateChatCompletionsOptions(GenerateReplyOptions? options, IEnumerable<IMessage> messages)
    {
        var oaiMessages = messages.Select(m => m switch
        {
            IMessage<ChatRequestMessage> chatRequestMessage => chatRequestMessage.Content,
            _ => throw new ArgumentException("Invalid message type")
        });

        // add system message if there's no system message in messages
        if (!oaiMessages.Any(m => m is ChatRequestSystemMessage))
        {
            oaiMessages = new[] { new ChatRequestSystemMessage(_systemMessage) }.Concat(oaiMessages);
        }

        var settings = new ChatCompletionsOptions(this.modelName, oaiMessages)
        {
            MaxTokens = options?.MaxToken ?? _maxTokens,
            Temperature = options?.Temperature ?? _temperature,
        };

        var openAIFunctionDefinitions = options?.Functions?.Select(f => f.ToOpenAIFunctionDefinition());
        var functions = openAIFunctionDefinitions ?? _functions;
        if (functions is not null && functions.Count() > 0)
        {
            foreach (var f in functions)
            {
                settings.Tools.Add(new ChatCompletionsFunctionToolDefinition(f));
            }
        }

        if (options?.StopSequence is var sequence && sequence is { Length: > 0 })
        {
            foreach (var seq in sequence)
            {
                settings.StopSequences.Add(seq);
            }
        }

        return settings;
    }
}
