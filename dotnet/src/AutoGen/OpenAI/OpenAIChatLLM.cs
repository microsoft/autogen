// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatLLM.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Azure.AI.OpenAI;

namespace AutoGen.OpenAI;

public class OpenAIChatLLM : IChatLLM
{
    private OpenAIClient _client;
    private readonly string _model;
    private readonly float _temperature;
    private readonly int _maxToken;
    private readonly string[]? _stopWords;
    private readonly FunctionDefinition[]? functionDefinitions;

    public OpenAIChatLLM(
        OpenAIClient client,
        string model,
        float temperature = 0.7f,
        int maxToken = 1024,
        string[]? stopWords = null,
        FunctionDefinition[]? functionDefinitions = null)
    {
        this._client = client;
        this._model = model;
        this._temperature = temperature;
        this._maxToken = maxToken;
        this._stopWords = stopWords;
        this.functionDefinitions = functionDefinitions;
    }

    public static OpenAIChatLLM Create(AzureOpenAIConfig config)
    {
        var client = new OpenAIClient(new Uri(config.Endpoint), new Azure.AzureKeyCredential(config.ApiKey));
        return new OpenAIChatLLM(client, config.DeploymentName);
    }

    public static OpenAIChatLLM Create(OpenAIConfig config)
    {
        var client = new OpenAIClient(config.ApiKey);
        return new OpenAIChatLLM(client, config.ModelId);
    }

    public async Task<IChatLLM.ChatCompletion> GetChatCompletionsAsync(
        IEnumerable<Message> messages,
        float? temperature = null,
        int? maxToken = null,
        string[]? stopWords = null,
        CancellationToken ct = default)
    {
        var chatMessages = messages.Select(m =>
        {
            if (m is { Value: ChatRequestMessage chatRequestMessage })
            {
                return chatRequestMessage;
            }

            if (m.Role == Role.User)
            {
                return m.ToChatRequestUserMessage();
            }

            if (m.Role == Role.System)
            {
                return m.ToChatRequestSystemMessage();
            }

            if (m.Role == Role.Function)
            {
                return m.ToChatRequestFunctionMessage();
            }

            if (m.Role == Role.Assistant)
            {
                return m.ToChatRequestAssistantMessage();
            }

            throw new System.Exception($"Unsupported message type {m.GetType()}");
        });

        var settings = new ChatCompletionsOptions(this._model, chatMessages)
        {
            Temperature = temperature ?? this._temperature,
            MaxTokens = maxToken ?? this._maxToken,
        };

        if (this.functionDefinitions != null)
        {
            settings.Functions = this.functionDefinitions;
        }
        var stopSequences = stopWords ?? this._stopWords;
        if (stopSequences != null)
        {
            foreach (var word in stopSequences)
            {
                settings.StopSequences.Add(word);
            }
        }

        var response = await this._client.GetChatCompletionsAsync(settings, ct);
        var oaiMessage = response.Value.Choices.First().Message;
        var totalToken = response.Value.Usage.TotalTokens;
        var message = new Message(Role.Assistant, oaiMessage.Content)
        {
            FunctionArguments = oaiMessage.FunctionCall?.Arguments,
            FunctionName = oaiMessage.FunctionCall?.Name,
            Value = oaiMessage,
        };

        return new IChatLLM.ChatCompletion
        {
            Message = message,
            CompletionTokens = response.Value.Usage.CompletionTokens,
            TotalTokens = response.Value.Usage.TotalTokens,
            PromptTokens = response.Value.Usage.PromptTokens,
        };
    }
}
