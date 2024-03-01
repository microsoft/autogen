// Copyright (c) Microsoft Corporation. All rights reserved.
// GPTAgent.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Core.Middleware;
using AutoGen.OpenAI.Middleware;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI;

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
public class GPTAgent : IStreamingAgent
{
    private readonly string _systemMessage;
    private readonly IEnumerable<FunctionDefinition>? _functions;
    private readonly float _temperature;
    private readonly int _maxTokens = 1024;
    private readonly IDictionary<string, Func<string, Task<string>>>? functionMap;
    private readonly OpenAIClient openAIClient;
    private readonly string? modelName;
    private readonly OpenAIClientAgent _innerAgent;

    public GPTAgent(
        string name,
        string systemMessage,
        ILLMConfig config,
        float temperature = 0.7f,
        int maxTokens = 1024,
        IEnumerable<FunctionDefinition>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null)
    {
        openAIClient = config switch
        {
            AzureOpenAIConfig azureConfig => new OpenAIClient(new Uri(azureConfig.Endpoint), new Azure.AzureKeyCredential(azureConfig.ApiKey)),
            OpenAIConfig openAIConfig => new OpenAIClient(openAIConfig.ApiKey),
            _ => throw new ArgumentException($"Unsupported config type {config.GetType()}"),
        };

        modelName = config switch
        {
            AzureOpenAIConfig azureConfig => azureConfig.DeploymentName,
            OpenAIConfig openAIConfig => openAIConfig.ModelId,
            _ => throw new ArgumentException($"Unsupported config type {config.GetType()}"),
        };

        _innerAgent = new OpenAIClientAgent(openAIClient, name, systemMessage, modelName, temperature, maxTokens, functions);
        _systemMessage = systemMessage;
        _functions = functions;
        Name = name;
        _temperature = temperature;
        _maxTokens = maxTokens;
        this.functionMap = functionMap;
    }

    public GPTAgent(
        string name,
        string systemMessage,
        OpenAIClient openAIClient,
        string modelName,
        float temperature = 0.7f,
        int maxTokens = 1024,
        IEnumerable<FunctionDefinition>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null)
    {
        this.openAIClient = openAIClient;
        this.modelName = modelName;
        _systemMessage = systemMessage;
        _functions = functions;
        Name = name;
        _temperature = temperature;
        _maxTokens = maxTokens;
        this.functionMap = functionMap;
        _innerAgent = new OpenAIClientAgent(openAIClient, name, systemMessage, modelName, temperature, maxTokens, functions);
    }

    public string Name { get; }

    public async Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var oaiConnectorMiddleware = new OpenAIMessageConnector();
        var agent = this._innerAgent.RegisterMiddleware(oaiConnectorMiddleware);
        if (this.functionMap is not null)
        {
            var functionMapMiddleware = new FunctionCallMiddleware(functionMap: this.functionMap);
            agent = agent.RegisterMiddleware(functionMapMiddleware);
        }

        return await agent.GenerateReplyAsync(messages, options, cancellationToken);
    }

    public async Task<IAsyncEnumerable<IMessage>> GenerateStreamingReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        var settings = this.CreateChatCompletionsOptions(options, messages);
        var response = await this.openAIClient.GetChatCompletionsStreamingAsync(settings, cancellationToken);
        return this.ProcessResponse(response);
    }

    private async IAsyncEnumerable<IMessage> ProcessResponse(StreamingResponse<StreamingChatCompletionsUpdate> response)
    {
        var content = string.Empty;
        string? functionName = default;
        string? functionArguments = default;
        await foreach (var chunk in response)
        {
            if (chunk?.FunctionName is not null)
            {
                functionName = chunk.FunctionName;
            }

            if (chunk?.FunctionArgumentsUpdate is not null)
            {
                if (functionArguments is null)
                {
                    functionArguments = chunk.FunctionArgumentsUpdate;
                }
                else
                {
                    functionArguments += chunk.FunctionArgumentsUpdate;
                }
            }

            if (chunk?.ContentUpdate is not null)
            {
                if (content is null)
                {
                    content = chunk.ContentUpdate;
                }
                else
                {
                    content += chunk.ContentUpdate;
                }
            }

            // case 1: plain text content
            // in this case we yield the message
            if (content is not null && functionName is null)
            {
                var msg = new TextMessage(Role.Assistant, content, from: this.Name);

                yield return msg;
                continue;
            }

            // case 2: function call
            // in this case, we yield the message once after function name is available and function args has been updated
            if (functionName is not null && functionArguments is not null)
            {
                var msg = new ToolCallMessage(functionName, functionArguments, from: this.Name);
                yield return msg;

                if (functionMap is not null && chunk?.FinishReason is not null && chunk.FinishReason == CompletionsFinishReason.FunctionCall)
                {
                    // call the function
                    if (this.functionMap.TryGetValue(functionName, out var func))
                    {
                        var result = await func(functionArguments);
                        yield return new ToolCallResultMessage(result, functionName, functionArguments, from: this.Name);
                    }
                    else
                    {
                        var errorMessage = $"Function {functionName} is not available. Available functions are: {string.Join(", ", this.functionMap.Select(f => f.Key))}";
                        yield return new ToolCallResultMessage(errorMessage, functionName, functionArguments, from: this.Name);
                    }
                }

                continue;
            }
        }
    }

    private ChatCompletionsOptions CreateChatCompletionsOptions(GenerateReplyOptions? options, IEnumerable<IMessage> messages)
    {
        var oaiMessages = this.ProcessMessages(messages);
        var settings = new ChatCompletionsOptions(this.modelName, oaiMessages)
        {
            MaxTokens = options?.MaxToken ?? _maxTokens,
            Temperature = options?.Temperature ?? _temperature,
        };

        var functions = options?.Functions ?? _functions;
        if (functions is not null && functions.Count() > 0)
        {
            foreach (var f in functions)
            {
                settings.Functions.Add(f);
            }
            //foreach (var f in functions)
            //{
            //    settings.Tools.Add(new ChatCompletionsFunctionToolDefinition(f));
            //}
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


    private IEnumerable<ChatRequestMessage> ProcessMessages(IEnumerable<IMessage> messages)
    {
        // add system message if there's no system message in messages
        var openAIMessages = messages.SelectMany(m => this.ToOpenAIChatRequestMessage(m)) ?? [];
        if (!openAIMessages.Any(m => m is ChatRequestSystemMessage))
        {
            openAIMessages = new[] { new ChatRequestSystemMessage(_systemMessage) }.Concat(openAIMessages);
        }

        return openAIMessages;
    }
}
