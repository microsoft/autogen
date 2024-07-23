// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI.Extension;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI;

/// <summary>
/// OpenAI client agent. This agent is a thin wrapper around <see cref="OpenAIClient"/> to provide a simple interface for chat completions.
/// To better work with other agents, it's recommended to use <see cref="GPTAgent"/> which supports more message types and have a better compatibility with other agents.
/// <para><see cref="OpenAIChatAgent" /> supports the following message types:</para>
/// <list type="bullet">
/// <item>
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="ChatRequestMessage"/>: chat request message.
/// </item>
/// </list>
/// <para><see cref="OpenAIChatAgent" /> returns the following message types:</para>
/// <list type="bullet">
/// <item>
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="ChatResponseMessage"/>: chat response message.
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="StreamingChatCompletionsUpdate"/>: streaming chat completions update.
/// </item>
/// </list>
/// </summary>
public class OpenAIChatAgent : IStreamingAgent
{
    private readonly OpenAIClient openAIClient;
    private readonly string modelName;
    private readonly float _temperature;
    private readonly int _maxTokens = 1024;
    private readonly IEnumerable<FunctionDefinition>? _functions;
    private readonly string _systemMessage;
    private readonly ChatCompletionsResponseFormat? _responseFormat;
    private readonly int? _seed;

    /// <summary>
    /// Create a new instance of <see cref="OpenAIChatAgent"/>.
    /// </summary>
    /// <param name="openAIClient">openai client</param>
    /// <param name="name">agent name</param>
    /// <param name="modelName">model name. e.g. gpt-turbo-3.5</param>
    /// <param name="systemMessage">system message</param>
    /// <param name="temperature">temperature</param>
    /// <param name="maxTokens">max tokens to generated</param>
    /// <param name="responseFormat">response format, set it to <see cref="ChatCompletionsResponseFormat.JsonObject"/> to enable json mode.</param>
    /// <param name="seed">seed to use, set it to enable deterministic output</param>
    /// <param name="functions">functions</param>
    public OpenAIChatAgent(
        OpenAIClient openAIClient,
        string name,
        string modelName,
        string systemMessage = "You are a helpful AI assistant",
        float temperature = 0.7f,
        int maxTokens = 1024,
        int? seed = null,
        ChatCompletionsResponseFormat? responseFormat = null,
        IEnumerable<FunctionDefinition>? functions = null)
    {
        this.openAIClient = openAIClient;
        this.modelName = modelName;
        this.Name = name;
        _temperature = temperature;
        _maxTokens = maxTokens;
        _functions = functions;
        _systemMessage = systemMessage;
        _responseFormat = responseFormat;
        _seed = seed;
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var settings = this.CreateChatCompletionsOptions(options, messages);
        var reply = await this.openAIClient.GetChatCompletionsAsync(settings, cancellationToken);

        return new MessageEnvelope<ChatCompletions>(reply, from: this.Name);
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var settings = this.CreateChatCompletionsOptions(options, messages);
        var response = await this.openAIClient.GetChatCompletionsStreamingAsync(settings, cancellationToken);
        await foreach (var update in response.WithCancellation(cancellationToken))
        {
            if (update.ChoiceIndex > 0)
            {
                throw new InvalidOperationException("Only one choice is supported in streaming response");
            }

            yield return new MessageEnvelope<StreamingChatCompletionsUpdate>(update, from: this.Name);
        }
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
            ResponseFormat = _responseFormat,
            Seed = _seed,
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
