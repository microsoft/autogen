// Copyright (c) Microsoft Corporation. All rights reserved.
// LMStudioAgent.cs

using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.OpenAI.V1;
using Azure.AI.OpenAI;
using Azure.Core.Pipeline;

namespace AutoGen.LMStudio;

/// <summary>
/// agent that consumes local server from LM Studio
/// </summary>
/// <example>
/// [!code-csharp[LMStudioAgent](../../samples/AutoGen.BasicSamples/Example08_LMStudio.cs?name=lmstudio_example_1)]
/// </example>
[Obsolete("Use OpenAIChatAgent to connect to LM Studio")]
public class LMStudioAgent : IAgent
{
    private readonly GPTAgent innerAgent;

    public LMStudioAgent(
        string name,
        LMStudioConfig config,
        string systemMessage = "You are a helpful AI assistant",
        float temperature = 0.7f,
        int maxTokens = 1024,
        IEnumerable<FunctionDefinition>? functions = null,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null)
    {
        var client = ConfigOpenAIClientForLMStudio(config);
        innerAgent = new GPTAgent(
            name: name,
            systemMessage: systemMessage,
            openAIClient: client,
            modelName: "llm", // model name doesn't matter for LM Studio
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

    private OpenAIClient ConfigOpenAIClientForLMStudio(LMStudioConfig config)
    {
        // create uri from host and port
        var uri = config.Uri;
        var handler = new CustomHttpClientHandler(uri);
        var httpClient = new HttpClient(handler);
        var option = new OpenAIClientOptions(OpenAIClientOptions.ServiceVersion.V2022_12_01)
        {
            Transport = new HttpClientTransport(httpClient),
        };

        return new OpenAIClient("api-key", option);
    }

    private sealed class CustomHttpClientHandler : HttpClientHandler
    {
        private Uri _modelServiceUrl;

        public CustomHttpClientHandler(Uri modelServiceUrl)
        {
            _modelServiceUrl = modelServiceUrl;
        }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            // request.RequestUri = new Uri($"{_modelServiceUrl}{request.RequestUri.PathAndQuery}");
            var uriBuilder = new UriBuilder(_modelServiceUrl);
            uriBuilder.Path = request.RequestUri?.PathAndQuery ?? throw new InvalidOperationException("RequestUri is null");
            request.RequestUri = uriBuilder.Uri;
            return base.SendAsync(request, cancellationToken);
        }
    }
}
