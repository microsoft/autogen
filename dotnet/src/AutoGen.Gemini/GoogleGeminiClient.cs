// Copyright (c) Microsoft Corporation. All rights reserved.
// GoogleGeminiClient.cs

using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Google.Cloud.AIPlatform.V1;
using Google.Protobuf;

namespace AutoGen.Gemini;

public class GoogleGeminiClient : IGeminiClient
{
    private readonly string apiKey;
    private const string endpoint = "https://generativelanguage.googleapis.com/v1beta";
    private readonly HttpClient httpClient = new();
    private const string generateContentPath = "models/{0}:generateContent";
    private const string generateContentStreamPath = "models/{0}:streamGenerateContent";

    public GoogleGeminiClient(HttpClient httpClient, string apiKey)
    {
        this.apiKey = apiKey;
        this.httpClient = httpClient;
    }

    public GoogleGeminiClient(string apiKey)
    {
        this.apiKey = apiKey;
    }

    public async Task<GenerateContentResponse> GenerateContentAsync(GenerateContentRequest request, CancellationToken cancellationToken = default)
    {
        var path = string.Format(generateContentPath, request.Model);
        var url = $"{endpoint}/{path}?key={apiKey}";

        var httpContent = new StringContent(JsonFormatter.Default.Format(request), System.Text.Encoding.UTF8, "application/json");
        var response = await httpClient.PostAsync(url, httpContent, cancellationToken);

        if (!response.IsSuccessStatusCode)
        {
            throw new ArgumentException($"Failed to generate content. Status code: {response.StatusCode}");
        }

#pragma warning disable CA2016 // Forward the CancellationToken parameter to the asynchronous method
        var json = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
#pragma warning restore CA2016 // Forward the CancellationToken parameter to the asynchronous method
        return GenerateContentResponse.Parser.ParseJson(json);
    }

    public async IAsyncEnumerable<GenerateContentResponse> GenerateContentStreamAsync(GenerateContentRequest request)
    {
        var path = string.Format(generateContentStreamPath, request.Model);
        var url = $"{endpoint}/{path}?key={apiKey}&alt=sse";

        var httpContent = new StringContent(JsonFormatter.Default.Format(request), System.Text.Encoding.UTF8, "application/json");
        var requestMessage = new HttpRequestMessage(HttpMethod.Post, url)
        {
            Content = httpContent
        };

        var response = await httpClient.SendAsync(requestMessage, HttpCompletionOption.ResponseHeadersRead);

        if (!response.IsSuccessStatusCode)
        {
            throw new ArgumentException($"Failed to generate content. Status code: {response.StatusCode}");
        }

        var stream = await response.Content.ReadAsStreamAsync();
        var jp = new JsonParser(JsonParser.Settings.Default.WithIgnoreUnknownFields(true));
        using var streamReader = new System.IO.StreamReader(stream);
        while (!streamReader.EndOfStream)
        {
            var json = await streamReader.ReadLineAsync();
            if (string.IsNullOrWhiteSpace(json))
            {
                continue;
            }

            json = json.Substring("data:".Length).Trim();
            yield return jp.Parse<GenerateContentResponse>(json);
        }
    }
}
