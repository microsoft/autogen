// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicClient.cs

using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.Anthropic.Converters;
using AutoGen.Anthropic.DTO;

namespace AutoGen.Anthropic;

public sealed class AnthropicClient : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;

    private static readonly JsonSerializerOptions JsonSerializerOptions = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    private static readonly JsonSerializerOptions JsonDeserializerOptions = new()
    {
        Converters = { new ContentBaseConverter() }
    };

    public AnthropicClient(HttpClient httpClient, string baseUrl, string apiKey)
    {
        _httpClient = httpClient;
        _baseUrl = baseUrl;

        _httpClient.DefaultRequestHeaders.Add("x-api-key", apiKey);
        _httpClient.DefaultRequestHeaders.Add("anthropic-version", "2023-06-01");
    }

    public async Task<ChatCompletionResponse> CreateChatCompletionsAsync(ChatCompletionRequest chatCompletionRequest,
        CancellationToken cancellationToken)
    {
        var httpResponseMessage = await SendRequestAsync(chatCompletionRequest, cancellationToken);
        var responseStream = await httpResponseMessage.Content.ReadAsStreamAsync();

        if (httpResponseMessage.IsSuccessStatusCode)
            return await DeserializeResponseAsync<ChatCompletionResponse>(responseStream, cancellationToken);

        ErrorResponse res = await DeserializeResponseAsync<ErrorResponse>(responseStream, cancellationToken);
        throw new Exception(res.Error?.Message);
    }

    public async IAsyncEnumerable<ChatCompletionResponse> StreamingChatCompletionsAsync(
        ChatCompletionRequest chatCompletionRequest, [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var httpResponseMessage = await SendRequestAsync(chatCompletionRequest, cancellationToken);
        using var reader = new StreamReader(await httpResponseMessage.Content.ReadAsStreamAsync());

        var currentEvent = new SseEvent();
        while (await reader.ReadLineAsync() is { } line)
        {
            if (!string.IsNullOrEmpty(line))
            {
                currentEvent.Data = line.Substring("data:".Length).Trim();
            }
            else
            {
                if (currentEvent.Data == "[DONE]")
                    continue;

                if (currentEvent.Data != null)
                {
                    yield return await JsonSerializer.DeserializeAsync<ChatCompletionResponse>(
                        new MemoryStream(Encoding.UTF8.GetBytes(currentEvent.Data)),
                        cancellationToken: cancellationToken) ?? throw new Exception("Failed to deserialize response");
                }
                else if (currentEvent.Data != null)
                {
                    var res = await JsonSerializer.DeserializeAsync<ErrorResponse>(
                        new MemoryStream(Encoding.UTF8.GetBytes(currentEvent.Data)), cancellationToken: cancellationToken);

                    throw new Exception(res?.Error?.Message);
                }

                // Reset the current event for the next one
                currentEvent = new SseEvent();
            }
        }
    }

    private Task<HttpResponseMessage> SendRequestAsync<T>(T requestObject, CancellationToken cancellationToken)
    {
        var httpRequestMessage = new HttpRequestMessage(HttpMethod.Post, _baseUrl);
        var jsonRequest = JsonSerializer.Serialize(requestObject, JsonSerializerOptions);
        httpRequestMessage.Content = new StringContent(jsonRequest, Encoding.UTF8, "application/json");
        return _httpClient.SendAsync(httpRequestMessage, cancellationToken);
    }

    private async Task<T> DeserializeResponseAsync<T>(Stream responseStream, CancellationToken cancellationToken)
    {
        return await JsonSerializer.DeserializeAsync<T>(responseStream, JsonDeserializerOptions, cancellationToken)
               ?? throw new Exception("Failed to deserialize response");
    }

    public void Dispose()
    {
        _httpClient.Dispose();
    }

    private struct SseEvent
    {
        public string? Data { get; set; }

        public SseEvent(string? data = null)
        {
            Data = data;
        }
    }
}
