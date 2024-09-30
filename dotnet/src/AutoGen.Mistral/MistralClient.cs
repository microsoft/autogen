// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralClient.cs

using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Security.Authentication;
using System.Text;
using System.Text.Json;
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
        chatCompletionRequest.Stream = false;
        var response = await HttpRequestRaw(HttpMethod.Post, chatCompletionRequest);
        response.EnsureSuccessStatusCode();

        var responseStream = await response.Content.ReadAsStreamAsync();
        return await JsonSerializer.DeserializeAsync<ChatCompletionResponse>(responseStream) ?? throw new Exception("Failed to deserialize response");
    }

    public async IAsyncEnumerable<ChatCompletionResponse> StreamingChatCompletionsAsync(ChatCompletionRequest chatCompletionRequest)
    {
        chatCompletionRequest.Stream = true;
        var response = await HttpRequestRaw(HttpMethod.Post, chatCompletionRequest, streaming: true);
        using var stream = await response.Content.ReadAsStreamAsync();
        using StreamReader reader = new StreamReader(stream);
        string? line = null;

        SseEvent currentEvent = new SseEvent();
        while ((line = await reader.ReadLineAsync()) != null)
        {
            if (!string.IsNullOrEmpty(line))
            {
                currentEvent.Data = line.Substring("data:".Length).Trim();
            }
            else // an empty line indicates the end of an event
            {
                if (currentEvent.Data == "[DONE]")
                {
                    continue;
                }
                else if (currentEvent.EventType == null)
                {
                    var res = await JsonSerializer.DeserializeAsync<ChatCompletionResponse>(
                        new MemoryStream(Encoding.UTF8.GetBytes(currentEvent.Data ?? string.Empty))) ?? throw new Exception("Failed to deserialize response");
                    yield return res;
                }
                else if (currentEvent.EventType != null)
                {
                    var res = await JsonSerializer.DeserializeAsync<ErrorResponse>(
                        new MemoryStream(Encoding.UTF8.GetBytes(currentEvent.Data ?? string.Empty)));
                    throw new ArgumentException(res?.Error.Message);
                }

                // Reset the current event for the next one
                currentEvent = new SseEvent();
            }
        }
    }

    protected async Task<HttpResponseMessage> HttpRequestRaw(HttpMethod verb, object postData, bool streaming = false)
    {
        var url = $"{baseUrl}/chat/completions";
        HttpResponseMessage response;
        string resultAsString;
        HttpRequestMessage req = new HttpRequestMessage(verb, url);

        if (postData != null)
        {
            if (postData is HttpContent)
            {
                req.Content = postData as HttpContent;
            }
            else
            {
                string jsonContent = JsonSerializer.Serialize(postData,
                    new JsonSerializerOptions() { DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull });
                var stringContent = new StringContent(jsonContent, Encoding.UTF8, "application/json");
                req.Content = stringContent;
            }
        }

        response = await this._httpClient.SendAsync(req,
            streaming ? HttpCompletionOption.ResponseHeadersRead : HttpCompletionOption.ResponseContentRead);

        if (response.IsSuccessStatusCode)
        {
            return response;
        }
        else
        {
            try
            {
                resultAsString = await response.Content.ReadAsStringAsync();
            }
            catch (Exception e)
            {
                resultAsString =
                    "Additionally, the following error was thrown when attempting to read the response content: " +
                    e.ToString();
            }

            if (response.StatusCode == System.Net.HttpStatusCode.Unauthorized)
            {
                throw new AuthenticationException(
                    "Mistral rejected your authorization, most likely due to an invalid API Key. Full API response follows: " +
                    resultAsString);
            }
            else if (response.StatusCode == System.Net.HttpStatusCode.InternalServerError)
            {
                throw new HttpRequestException(
                    "Mistral had an internal server error, which can happen occasionally.  Please retry your request.  " +
                    GetErrorMessage(resultAsString, response, url, url));
            }
            else
            {
                throw new HttpRequestException(GetErrorMessage(resultAsString, response, url, url));
            }
        }
    }

    private string GetErrorMessage(string resultAsString, HttpResponseMessage response, string name, string description = "")
    {
        return $"Error at {name} ({description}) with HTTP status code: {response.StatusCode}. Content: {resultAsString ?? "<no content>"}";
    }

    public void Dispose()
    {
        _httpClient.Dispose();
    }

    public class SseEvent
    {
        public SseEvent(string? eventType = null, string? data = null)
        {
            EventType = eventType;
            Data = data;
        }

        public string? EventType { get; set; }
        public string? Data { get; set; }
    }
}
