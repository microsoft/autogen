// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatCompletionsClientAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.AzureAIInference.Extension;
using AutoGen.Core;
using Azure.AI.Inference;

namespace AutoGen.AzureAIInference;

/// <summary>
/// ChatCompletions client agent. This agent is a thin wrapper around <see cref="ChatCompletionsClient"/> to provide a simple interface for chat completions.
/// <para><see cref="ChatCompletionsClientAgent" /> supports the following message types:</para>
/// <list type="bullet">
/// <item>
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="ChatRequestMessage"/>: chat request message.
/// </item>
/// </list>
/// <para><see cref="ChatCompletionsClientAgent" /> returns the following message types:</para>
/// <list type="bullet">
/// <item>
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="ChatResponseMessage"/>: chat response message.
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="StreamingChatCompletionsUpdate"/>: streaming chat completions update.
/// </item>
/// </list>
/// </summary>
public class ChatCompletionsClientAgent : IStreamingAgent
{
    private readonly ChatCompletionsClient chatCompletionsClient;
    private readonly ChatCompletionsOptions options;
    private readonly string systemMessage;

    /// <summary>
    /// Create a new instance of <see cref="ChatCompletionsClientAgent"/>.
    /// </summary>
    /// <param name="chatCompletionsClient">chat completions client</param>
    /// <param name="name">agent name</param>
    /// <param name="modelName">model name. e.g. gpt-turbo-3.5</param>
    /// <param name="systemMessage">system message</param>
    /// <param name="temperature">temperature</param>
    /// <param name="maxTokens">max tokens to generated</param>
    /// <param name="responseFormat">response format, set it to <see cref="ChatCompletionsResponseFormatJSON"/> to enable json mode.</param>
    /// <param name="seed">seed to use, set it to enable deterministic output</param>
    /// <param name="functions">functions</param>
    public ChatCompletionsClientAgent(
        ChatCompletionsClient chatCompletionsClient,
        string name,
        string modelName,
        string systemMessage = "You are a helpful AI assistant",
        float temperature = 0.7f,
        int maxTokens = 1024,
        int? seed = null,
        ChatCompletionsResponseFormat? responseFormat = null,
        IEnumerable<FunctionDefinition>? functions = null)
        : this(
            chatCompletionsClient: chatCompletionsClient,
            name: name,
            options: CreateChatCompletionOptions(modelName, temperature, maxTokens, seed, responseFormat, functions),
            systemMessage: systemMessage)
    {
    }

    /// <summary>
    /// Create a new instance of <see cref="ChatCompletionsClientAgent"/>.
    /// </summary>
    /// <param name="chatCompletionsClient">chat completions client</param>
    /// <param name="name">agent name</param>
    /// <param name="systemMessage">system message</param>
    /// <param name="options">chat completion option. The option can't contain messages</param>
    public ChatCompletionsClientAgent(
        ChatCompletionsClient chatCompletionsClient,
        string name,
        ChatCompletionsOptions options,
        string systemMessage = "You are a helpful AI assistant")
    {
        if (options.Messages is { Count: > 0 })
        {
            throw new ArgumentException("Messages should not be provided in options");
        }

        this.chatCompletionsClient = chatCompletionsClient;
        this.Name = name;
        this.options = options;
        this.systemMessage = systemMessage;
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var settings = this.CreateChatCompletionsOptions(options, messages);
        var reply = await this.chatCompletionsClient.CompleteAsync(settings, cancellationToken: cancellationToken);

        return new MessageEnvelope<ChatCompletions>(reply, from: this.Name);
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var settings = this.CreateChatCompletionsOptions(options, messages);
        var response = await this.chatCompletionsClient.CompleteStreamingAsync(settings, cancellationToken);
        await foreach (var update in response.WithCancellation(cancellationToken))
        {
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
            oaiMessages = new[] { new ChatRequestSystemMessage(systemMessage) }.Concat(oaiMessages);
        }

        // clone the options by serializing and deserializing
        var json = JsonSerializer.Serialize(this.options);
        var settings = JsonSerializer.Deserialize<ChatCompletionsOptions>(json) ?? throw new InvalidOperationException("Failed to clone options");

        foreach (var m in oaiMessages)
        {
            settings.Messages.Add(m);
        }

        settings.Temperature = options?.Temperature ?? settings.Temperature;
        settings.MaxTokens = options?.MaxToken ?? settings.MaxTokens;

        foreach (var functions in this.options.Tools)
        {
            settings.Tools.Add(functions);
        }

        foreach (var stopSequence in this.options.StopSequences)
        {
            settings.StopSequences.Add(stopSequence);
        }

        var openAIFunctionDefinitions = options?.Functions?.Select(f => f.ToAzureAIInferenceFunctionDefinition()).ToList();
        if (openAIFunctionDefinitions is { Count: > 0 })
        {
            foreach (var f in openAIFunctionDefinitions)
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

    private static ChatCompletionsOptions CreateChatCompletionOptions(
        string modelName,
        float temperature = 0.7f,
        int maxTokens = 1024,
        int? seed = null,
        ChatCompletionsResponseFormat? responseFormat = null,
        IEnumerable<FunctionDefinition>? functions = null)
    {
        var options = new ChatCompletionsOptions()
        {
            Model = modelName,
            Temperature = temperature,
            MaxTokens = maxTokens,
            Seed = seed,
            ResponseFormat = responseFormat,
        };

        if (functions is not null)
        {
            foreach (var f in functions)
            {
                options.Tools.Add(new ChatCompletionsFunctionToolDefinition(f));
            }
        }

        return options;
    }
}
