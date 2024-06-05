// Copyright (c) Microsoft Corporation. All rights reserved.
// GoogleGeminiClient.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Google.Cloud.AIPlatform.V1;

namespace AutoGen.Gemini;

public class GoogleGeminiClient : IGeminiClient
{
    private readonly string apiKey;
    private const string endpoint = "https://generativelanguage.googleapis.com/v1beta";
    private readonly PredictionServiceClient client;
    public GoogleGeminiClient(string apiKey)
    {
        this.apiKey = apiKey;
        PredictionServiceClientBuilder builder = new()
        {
            Endpoint = endpoint,
        };

        this.client = builder.Build();
    }
    public Task<GenerateContentResponse> GenerateContentAsync(GenerateContentRequest request, CancellationToken cancellationToken = default)
    {
        throw new NotImplementedException();
    }

    public IAsyncEnumerable<GenerateContentResponse> GenerateContentStreamAsync(GenerateContentRequest request)
    {
        throw new NotImplementedException();
    }
}
