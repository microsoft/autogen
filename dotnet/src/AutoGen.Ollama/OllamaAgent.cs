// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaAgent.cs

using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using AutoGen.OpenAI;
using Azure.AI.OpenAI;
using Azure.Core.Pipeline;
using Azure.Core;

namespace AutoGen.Ollama;

/// <summary>
/// agent that consumes local server from LM Studio
/// </summary>
/// <example>
/// [!code-csharp[OllamaAgent](../../sample/AutoGen.BasicSamples/Example08_Ollama.cs?name=Ollama_example_1)]
/// </example>
public class OllamaAgent : IAgent
{
    private readonly GPTAgent innerAgent;

    public OllamaAgent(
        string name,
        OllamaConfig config,
        string modelName = "llama3:latest",
        string systemMessage = "You are a helpful AI assistant",
        float temperature = 0.7f,
        int maxTokens = 1024,
        IEnumerable<FunctionDefinition>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null)
    {
        var client = ConfigOpenAIClientForOllama(config);
        innerAgent = new GPTAgent(
            name: name,
            modelName: modelName,
            systemMessage: systemMessage,
            openAIClient: client,
            temperature: temperature,
            maxTokens: maxTokens,
            functions: functions,
            functionMap: functionMap);
    }

    public string Name => innerAgent.Name;

    public Task<IMessage> GenerateReplyAsync(
        IEnumerable<IMessage> messages,
        GenerateReplyOptions? options = null,
        System.Threading.CancellationToken cancellationToken = default)
    {
        return innerAgent.GenerateReplyAsync(messages, options, cancellationToken);
    }

    private OpenAIClient ConfigOpenAIClientForOllama(OllamaConfig config)
    {
        // create uri from host and port
        var uri = config.Uri;
        var accessToken = new AccessToken(string.Empty, DateTimeOffset.Now.AddDays(180));
        var tokenCredential = DelegatedTokenCredential.Create((_, _) => accessToken);
        var openAIClient = new OpenAIClient(uri, tokenCredential);

        // remove authenication header from pipeline
        var pipeline = HttpPipelineBuilder.Build(
            new OpenAIClientOptions(OpenAIClientOptions.ServiceVersion.V2022_12_01),
            Array.Empty<HttpPipelinePolicy>(),
            [],
            new ResponseClassifier());

        // use reflection to override _pipeline field
        var field = typeof(OpenAIClient).GetField("_pipeline", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field.SetValue(openAIClient, pipeline);

        // use reflection to set _isConfiguredForAzureOpenAI to false
        var isConfiguredForAzureOpenAIField = typeof(OpenAIClient).GetField("_isConfiguredForAzureOpenAI", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        isConfiguredForAzureOpenAIField.SetValue(openAIClient, false);

        return openAIClient;
    }
}
