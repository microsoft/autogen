// Copyright (c) Microsoft Corporation. All rights reserved.
// GenericAgent.cs

using System;
using System.Collections.Generic;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI;
using Azure.AI.OpenAI;
using Azure.Core;
using Azure.Core.Pipeline;

namespace AutoGen.GenericAPI;

/// <summary>
///     agent that consumes api's other than AzureOpenAI or OpenAI
/// </summary>
/// <example>
///     [!code-csharp[GenericAgent](../../sample/AutoGen.BasicSamples/Example10_GenericAPI.cs?name=genericapi_example_1)]
/// </example>
public class GenericAgent : IAgent
{
    private readonly GPTAgent innerAgent;

    public GenericAgent(
        string name,
        GenericAgentConfig config,
        string systemMessage = "You are a helpful AI assistant",
        float temperature = 0.7f,
        int maxTokens = 1024,
        IEnumerable<FunctionDefinition>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null)
    {
        OpenAIClient client = ConfigOpenAIClientForGenericApi(config);
        innerAgent = new GPTAgent(
            name,
            systemMessage,
            client,
            config.ModelName,
            temperature,
            maxTokens,
            functions,
            functionMap);
    }

    public string? Name => innerAgent.Name;

    public Task<Message> GenerateReplyAsync(
        IEnumerable<Message> messages,
        GenerateReplyOptions? options = null,
        CancellationToken cancellationToken = default)
    {
        return innerAgent.GenerateReplyAsync(messages, options, cancellationToken);
    }

    private OpenAIClient ConfigOpenAIClientForGenericApi(GenericAgentConfig config)
    {
        // create uri from host and port
        Uri uri = config.Uri;
        var accessToken = new AccessToken(config.ApiToken, DateTimeOffset.Now.AddDays(180));
        TokenCredential tokenCredential = DelegatedTokenCredential.Create((_, _) => accessToken);
        var openAIClient = new OpenAIClient(uri, tokenCredential);

        HttpPipeline pipeline = HttpPipelineBuilder.Build(
            new OpenAIClientOptions(OpenAIClientOptions.ServiceVersion.V2022_12_01),
            string.IsNullOrEmpty(config.ApiToken)
                ? Array.Empty<HttpPipelinePolicy>()
                : new[] { new AddAuthenticationHeaderPolicy("Bearer " + accessToken.Token) },
            [],
            new ResponseClassifier());

        // use reflection to override _pipeline field
        FieldInfo? field = typeof(OpenAIClient).GetField("_pipeline", BindingFlags.NonPublic | BindingFlags.Instance);
        field.SetValue(openAIClient, pipeline);

        // use reflection to set _isConfiguredForAzureOpenAI to false
        FieldInfo? isConfiguredForAzureOpenAIField = typeof(OpenAIClient).GetField("_isConfiguredForAzureOpenAI",
            BindingFlags.NonPublic | BindingFlags.Instance);
        isConfiguredForAzureOpenAIField.SetValue(openAIClient, false);

        return openAIClient;
    }
}

public class AddAuthenticationHeaderPolicy : HttpPipelineSynchronousPolicy
{
    private readonly string _headerValue;

    public AddAuthenticationHeaderPolicy(string headerValue)
    {
        _headerValue = headerValue;
    }

    public override void OnSendingRequest(HttpMessage message)
    {
        if (!string.IsNullOrEmpty(_headerValue))
        {
            message.Request.Headers.Add("Authorization", _headerValue);
        }
    }
}
