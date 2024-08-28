// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI.Extension;
using global::OpenAI;
using global::OpenAI.Chat;

namespace AutoGen.OpenAI;

/// <summary>
/// OpenAI client agent. This agent is a thin wrapper around <see cref="OpenAIClient"/> to provide a simple interface for chat completions.
/// <para><see cref="OpenAIChatAgent" /> supports the following message types:</para>
/// <list type="bullet">
/// <item>
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="ChatMessage"/>: chat message.
/// </item>
/// </list>
/// <para><see cref="OpenAIChatAgent" /> returns the following message types:</para>
/// <list type="bullet">
/// <item>
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="ChatCompletion"/>: chat response message.
/// <see cref="MessageEnvelope{T}"/> where T is <see cref="StreamingChatCompletionUpdate"/>: streaming chat completions update.
/// </item>
/// </list>
/// </summary>
public class OpenAIChatAgent : IStreamingAgent
{
    private readonly ChatClient chatClient;
    private readonly ChatCompletionOptions options;
    private readonly string systemMessage;

    /// <summary>
    /// Create a new instance of <see cref="OpenAIChatAgent"/>.
    /// </summary>
    /// <param name="chatClient">openai client</param>
    /// <param name="name">agent name</param>
    /// <param name="systemMessage">system message</param>
    /// <param name="temperature">temperature</param>
    /// <param name="maxTokens">max tokens to generated</param>
    /// <param name="responseFormat">response format, set it to <see cref="ChatResponseFormat.JsonObject"/> to enable json mode.</param>
    /// <param name="seed">seed to use, set it to enable deterministic output</param>
    /// <param name="functions">functions</param>
    public OpenAIChatAgent(
        ChatClient chatClient,
        string name,
        string systemMessage = "You are a helpful AI assistant",
        float temperature = 0.7f,
        int maxTokens = 1024,
        int? seed = null,
        ChatResponseFormat? responseFormat = null,
        IEnumerable<ChatTool>? functions = null)
        : this(
            chatClient: chatClient,
            name: name,
            options: CreateChatCompletionOptions(temperature, maxTokens, seed, responseFormat, functions),
            systemMessage: systemMessage)
    {
    }

    /// <summary>
    /// Create a new instance of <see cref="OpenAIChatAgent"/>.
    /// </summary>
    /// <param name="chatClient">openai chat client</param>
    /// <param name="name">agent name</param>
    /// <param name="systemMessage">system message</param>
    /// <param name="options">chat completion option. The option can't contain messages</param>
    public OpenAIChatAgent(
        ChatClient chatClient,
        string name,
        ChatCompletionOptions options,
        string systemMessage = "You are a helpful AI assistant")
    {
        this.chatClient = chatClient;
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
        var chatHistory = this.CreateChatMessages(messages);
        var settings = this.CreateChatCompletionsOptions(options);
        var reply = await this.chatClient.CompleteChatAsync(chatHistory, settings, cancellationToken);
        return new MessageEnvelope<ChatCompletion>(reply.Value, from: this.Name);
    }

    public async IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var chatHistory = this.CreateChatMessages(messages);
        var settings = this.CreateChatCompletionsOptions(options);
        var response = this.chatClient.CompleteChatStreamingAsync(chatHistory, settings, cancellationToken);
        await foreach (var update in response.WithCancellation(cancellationToken))
        {
            if (update.ContentUpdate.Count > 1)
            {
                throw new InvalidOperationException("Only one choice is supported in streaming response");
            }

            yield return new MessageEnvelope<StreamingChatCompletionUpdate>(update, from: this.Name);
        }
    }

    private IEnumerable<ChatMessage> CreateChatMessages(IEnumerable<IMessage> messages)
    {
        var oaiMessages = messages.Select(m => m switch
        {
            IMessage<ChatMessage> chatMessage => chatMessage.Content,
            _ => throw new ArgumentException("Invalid message type")
        });

        // add system message if there's no system message in messages
        if (!oaiMessages.Any(m => m is SystemChatMessage))
        {
            oaiMessages = new[] { new SystemChatMessage(systemMessage) }.Concat(oaiMessages);
        }

        return oaiMessages;
    }

    private ChatCompletionOptions CreateChatCompletionsOptions(GenerateReplyOptions? options)
    {
        var option = new ChatCompletionOptions()
        {
            Seed = this.options.Seed,
            Temperature = options?.Temperature ?? this.options.Temperature,
            MaxTokens = options?.MaxToken ?? this.options.MaxTokens,
            ResponseFormat = this.options.ResponseFormat,
            FrequencyPenalty = this.options.FrequencyPenalty,
            FunctionChoice = this.options.FunctionChoice,
            IncludeLogProbabilities = this.options.IncludeLogProbabilities,
            ParallelToolCallsEnabled = this.options.ParallelToolCallsEnabled,
            PresencePenalty = this.options.PresencePenalty,
            ToolChoice = this.options.ToolChoice,
            TopLogProbabilityCount = this.options.TopLogProbabilityCount,
            TopP = this.options.TopP,
            EndUserId = this.options.EndUserId,
        };

        // add tools from this.options to option
        foreach (var tool in this.options.Tools)
        {
            option.Tools.Add(tool);
        }

        // add stop sequences from this.options to option
        foreach (var seq in this.options.StopSequences)
        {
            option.StopSequences.Add(seq);
        }

        var openAIFunctionDefinitions = options?.Functions?.Select(f => f.ToChatTool()).ToList();
        if (openAIFunctionDefinitions is { Count: > 0 })
        {
            foreach (var f in openAIFunctionDefinitions)
            {
                option.Tools.Add(f);
            }
        }

        if (options?.StopSequence is var sequence && sequence is { Length: > 0 })
        {
            foreach (var seq in sequence)
            {
                option.StopSequences.Add(seq);
            }
        }

        return option;
    }

    private static ChatCompletionOptions CreateChatCompletionOptions(
        float temperature = 0.7f,
        int maxTokens = 1024,
        int? seed = null,
        ChatResponseFormat? responseFormat = null,
        IEnumerable<ChatTool>? functions = null)
    {
        var options = new ChatCompletionOptions
        {
            Temperature = temperature,
            MaxTokens = maxTokens,
            Seed = seed,
            ResponseFormat = responseFormat,
        };

        if (functions is not null)
        {
            foreach (var f in functions)
            {
                options.Tools.Add(f);
            }
        }

        return options;
    }
}
