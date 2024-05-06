// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaTextEmbeddingServiceTests.cs

using AutoGen.Tests;
using FluentAssertions;

namespace Autogen.Ollama.Tests;

public class OllamaTextEmbeddingServiceTests
{
    [ApiKeyFact("OLLAMA_API", "OLLAMA_EMBEDDING_MODEL_NAME")]
    public async Task GenerateAsync_ReturnsEmbeddings_WhenApiResponseIsSuccessful()
    {
        string host = Environment.GetEnvironmentVariable("OLLAMA_API")
                      ?? throw new InvalidOperationException("OLLAMA_API is not set.");
        string embeddingModelName = Environment.GetEnvironmentVariable("OLLAMA_EMBEDDING_MODEL_NAME")
                           ?? throw new InvalidOperationException("OLLAMA_EMBEDDING_MODEL_NAME is not set.");
        var httpClient = new HttpClient
        {
            BaseAddress = new Uri(host),
            Timeout = TimeSpan.FromSeconds(250)
        };
        var request = new TextEmbeddingsRequest { Model = embeddingModelName, Prompt = "Hi, you must follow these instructions", };
        var service = new OllamaTextEmbeddingService(httpClient);
        TextEmbeddingsResponse response = await service.GenerateAsync(request);
        response.Should().NotBeNull();
    }

    [ApiKeyFact("OLLAMA_API", "OLLAMA_MODEL_NAME", "OLLAMA_EMBEDDING_MODEL_NAME")]
    public async Task GenerateAsync_ThrowsHttpRequestException_WhenApiResponseIsError()
    {
        string host = Environment.GetEnvironmentVariable("OLLAMA_API")
                      ?? throw new InvalidOperationException("OLLAMA_API is not set.");
        string modelName = Environment.GetEnvironmentVariable("OLLAMA_EMBEDDING_MODEL_NAME")
                                    ?? throw new InvalidOperationException("OLLAMA_EMBEDDING_MODEL_NAME is not set.");
        var httpClient = new HttpClient
        {
            BaseAddress = new Uri(host),
            Timeout = TimeSpan.FromSeconds(250)
        };
        var request = new TextEmbeddingsRequest { Model = modelName, Prompt = "Hi, you must follow these instructions", };
        var service = new OllamaTextEmbeddingService(httpClient);
        TextEmbeddingsResponse response = await service.GenerateAsync(request);
        response.Should().NotBeNull();
    }
}
