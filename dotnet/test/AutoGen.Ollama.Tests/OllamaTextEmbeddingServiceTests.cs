// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaTextEmbeddingServiceTests.cs

using AutoGen.Tests;
using FluentAssertions;

namespace AutoGen.Ollama.Tests;

public class OllamaTextEmbeddingServiceTests
{
    [ApiKeyFact("OLLAMA_HOST", "OLLAMA_EMBEDDING_MODEL_NAME")]
    public async Task GenerateAsync_ReturnsEmbeddings_WhenApiResponseIsSuccessful()
    {
        string host = Environment.GetEnvironmentVariable("OLLAMA_HOST")
                      ?? throw new InvalidOperationException("OLLAMA_HOST is not set.");
        string embeddingModelName = Environment.GetEnvironmentVariable("OLLAMA_EMBEDDING_MODEL_NAME")
                           ?? throw new InvalidOperationException("OLLAMA_EMBEDDING_MODEL_NAME is not set.");
        var httpClient = new HttpClient
        {
            BaseAddress = new Uri(host)
        };
        var request = new TextEmbeddingsRequest { Model = embeddingModelName, Prompt = "Llamas are members of the camelid family", };
        var service = new OllamaTextEmbeddingService(httpClient);
        TextEmbeddingsResponse response = await service.GenerateAsync(request);
        response.Should().NotBeNull();
    }
}
