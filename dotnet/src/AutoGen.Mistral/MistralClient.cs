// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralClient.cs

using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace AutoGen.Mistral;

public class MistralClient : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly string baseUrl = "https://api.mistral.ai/v1";

    public MistralClient(string apiKey, string? baseUrl = null)
    {
        _httpClient = new HttpClient();
        _httpClient.DefaultRequestHeaders.Accept.Add(new System.Net.Http.Headers.MediaTypeWithQualityHeaderValue("application/json"));
        _httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");
        this.baseUrl = baseUrl ?? this.baseUrl;
    }

    public MistralClient(HttpClient httpClient, string? baseUrl = null)
    {
        _httpClient = httpClient;
        _httpClient.DefaultRequestHeaders.Accept.Add(new System.Net.Http.Headers.MediaTypeWithQualityHeaderValue("application/json"));
        this.baseUrl = baseUrl ?? this.baseUrl;
    }

    public async Task<ChatCompletionResponse> CreateChatCompletionsAsync(ChatCompletionRequest chatCompletionRequest)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, $"{baseUrl}/chat/completions");
        //request.Content = new StringContent(System.Text.Json.JsonSerializer.Serialize(chatCompletionRequest), System.Text.Encoding.UTF8, "application/json");
        var json = System.Text.Json.JsonSerializer.Serialize(chatCompletionRequest, new System.Text.Json.JsonSerializerOptions() { DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull });
        var jsonContent = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
        request.Content = jsonContent;
        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        var responseStream = await response.Content.ReadAsStreamAsync();
        return await System.Text.Json.JsonSerializer.DeserializeAsync<ChatCompletionResponse>(responseStream) ?? throw new Exception("Failed to deserialize response");
    }

    public async Task<IAsyncEnumerable<ChatCompletionResponse>> CreateStreamingChatCompletionsAsync(ChatCompletionRequest chatCompletionRequest)
    {
        throw new NotImplementedException();
    }

    public void Dispose()
    {
        _httpClient.Dispose();
    }
}
