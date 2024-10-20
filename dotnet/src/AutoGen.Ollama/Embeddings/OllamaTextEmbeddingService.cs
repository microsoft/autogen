// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaTextEmbeddingService.cs

using System;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen.Ollama;

public class OllamaTextEmbeddingService : ITextEmbeddingService
{
    private readonly HttpClient _client;

    public OllamaTextEmbeddingService(HttpClient client)
    {
        _client = client;
    }
    public async Task<TextEmbeddingsResponse> GenerateAsync(TextEmbeddingsRequest request, CancellationToken cancellationToken = default)
    {
        using (HttpResponseMessage? response = await _client
                   .SendAsync(BuildPostRequest(request), HttpCompletionOption.ResponseContentRead, cancellationToken))
        {
            response.EnsureSuccessStatusCode();

            Stream? streamResponse = await response.Content.ReadAsStreamAsync();
            TextEmbeddingsResponse output = await JsonSerializer
                                                .DeserializeAsync<TextEmbeddingsResponse>(streamResponse, cancellationToken: cancellationToken)
                                            ?? throw new Exception("Failed to deserialize response");
            return output;
        }
    }
    private static HttpRequestMessage BuildPostRequest(TextEmbeddingsRequest request)
    {
        string serialized = JsonSerializer.Serialize(request);
        return new HttpRequestMessage(HttpMethod.Post, OllamaConsts.EmbeddingsEndpoint)
        {
            Content = new StringContent(serialized, Encoding.UTF8, OllamaConsts.JsonMediaType)
        };
    }
}
