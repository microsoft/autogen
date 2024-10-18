// Copyright (c) Microsoft Corporation. All rights reserved.
// GPTAgent.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI.V1.Extension;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI.V1;

/// <summary>
/// GPT agent that can be used to connect to OpenAI chat models like GPT-3.5, GPT-4, etc.
/// <para><see cref="GPTAgent" /> supports the following message types as input:</para>
/// <para>- <see cref="TextMessage"/></para> 
/// <para>- <see cref="ImageMessage"/></para> 
/// <para>- <see cref="MultiModalMessage"/></para>
/// <para>- <see cref="ToolCallMessage"/></para>
/// <para>- <see cref="ToolCallResultMessage"/></para>
/// <para>- <see cref="Message"/></para>
/// <para>- <see cref="IMessage{ChatRequestMessage}"/> where T is <see cref="ChatRequestMessage"/></para>
/// <para>- <see cref="AggregateMessage{TMessage1, TMessage2}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/></para>
/// 
/// <para><see cref="GPTAgent" /> returns the following message types:</para>
/// <para>- <see cref="TextMessage"/></para> 
/// <para>- <see cref="ToolCallMessage"/></para>
/// <para>- <see cref="AggregateMessage{TMessage1, TMessage2}"/> where TMessage1 is <see cref="ToolCallMessage"/> and TMessage2 is <see cref="ToolCallResultMessage"/></para>
/// </summary>
[Obsolete("Use OpenAIChatAgent instead")]
public class GPTAgent : IStreamingAgent
{
    private readonly OpenAIClient openAIClient;
    private readonly IStreamingAgent _innerAgent;

    public GPTAgent(
        string name,
        string systemMessage,
        ILLMConfig config,
        float temperature = 0.7f,
        int maxTokens = 1024,
        int? seed = null,
        ChatCompletionsResponseFormat? responseFormat = null,
        IEnumerable<FunctionDefinition>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null)
    {
        openAIClient = config switch
        {
            AzureOpenAIConfig azureConfig => new OpenAIClient(new Uri(azureConfig.Endpoint), new Azure.AzureKeyCredential(azureConfig.ApiKey)),
            OpenAIConfig openAIConfig => new OpenAIClient(openAIConfig.ApiKey),
            _ => throw new ArgumentException($"Unsupported config type {config.GetType()}"),
        };

        var modelName = config switch
        {
            AzureOpenAIConfig azureConfig => azureConfig.DeploymentName,
            OpenAIConfig openAIConfig => openAIConfig.ModelId,
            _ => throw new ArgumentException($"Unsupported config type {config.GetType()}"),
        };

        _innerAgent = new OpenAIChatAgent(openAIClient, name, modelName, systemMessage, temperature, maxTokens, seed, responseFormat, functions)
            .RegisterMessageConnector();

        if (functionMap is not null)
        {
            var functionMapMiddleware = new FunctionCallMiddleware(functionMap: functionMap);
            _innerAgent = _innerAgent.RegisterStreamingMiddleware(functionMapMiddleware);
        }

        Name = name;
    }

    public GPTAgent(
        string name,
        string systemMessage,
        OpenAIClient openAIClient,
        string modelName,
        float temperature = 0.7f,
        int maxTokens = 1024,
        int? seed = null,
        ChatCompletionsResponseFormat? responseFormat = null,
        IEnumerable<FunctionDefinition>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null)
    {
        this.openAIClient = openAIClient;
        Name = name;

        _innerAgent = new OpenAIChatAgent(openAIClient, name, modelName, systemMessage, temperature, maxTokens, seed, responseFormat, functions)
            .RegisterMessageConnector();

        if (functionMap is not null)
        {
            var functionMapMiddleware = new FunctionCallMiddleware(functionMap: functionMap);
            _innerAgent = _innerAgent.RegisterStreamingMiddleware(functionMapMiddleware);
        }
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return await _innerAgent.GenerateReplyAsync(messages, options, cancellationToken);
    }

    public IAsyncEnumerable<IMessage> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return _innerAgent.GenerateStreamingReplyAsync(messages, options, cancellationToken);
    }
}
