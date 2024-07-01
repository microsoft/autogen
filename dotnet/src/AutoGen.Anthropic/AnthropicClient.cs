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
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        Converters = { new ContentBaseConverter(), new JsonPropertyNameEnumConverter<ToolChoiceType>() }
    };

    private static readonly JsonSerializerOptions JsonDeserializerOptions = new()
    {
        Converters = { new ContentBaseConverter(), new JsonPropertyNameEnumConverter<ToolChoiceType>() }
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
                if (line.StartsWith("event:"))
                {
                    currentEvent.EventType = line.Substring("event:".Length).Trim();
                }
                else if (line.StartsWith("data:"))
                {
                    currentEvent.Data = line.Substring("data:".Length).Trim();
                }
            }
            else // an empty line indicates the end of an event
            {
                if (currentEvent.EventType == "content_block_start" && !string.IsNullOrEmpty(currentEvent.Data))
                {
                    var dataBlock = JsonSerializer.Deserialize<DataBlock>(currentEvent.Data!);
                    if (dataBlock != null && dataBlock.ContentBlock?.Type == "tool_use")
                    {
                        currentEvent.ContentBlock = dataBlock.ContentBlock;
                    }
                }

                if (currentEvent.EventType is "message_start" or "content_block_delta" or "message_delta" && currentEvent.Data != null)
                {
                    var res = await JsonSerializer.DeserializeAsync<ChatCompletionResponse>(
                        new MemoryStream(Encoding.UTF8.GetBytes(currentEvent.Data)),
                        cancellationToken: cancellationToken);

                    if (res == null)
                    {
                        throw new Exception("Failed to deserialize response");
                    }

                    if (res.Delta?.Type == "input_json_delta" && !string.IsNullOrEmpty(res.Delta.PartialJson) &&
                        currentEvent.ContentBlock != null)
                    {
                        currentEvent.ContentBlock.AppendDeltaParameters(res.Delta.PartialJson!);
                    }
                    else if (res.Delta is { StopReason: "tool_use" } && currentEvent.ContentBlock != null)
                    {
                        if (res.Content == null)
                        {
                            res.Content = [currentEvent.ContentBlock.CreateToolUseContent()];
                        }
                        else
                        {
                            res.Content.Add(currentEvent.ContentBlock.CreateToolUseContent());
                        }

                        currentEvent = new SseEvent();
                    }

                    yield return res;
                }
                else if (currentEvent.EventType == "error" && currentEvent.Data != null)
                {
                    var res = await JsonSerializer.DeserializeAsync<ErrorResponse>(
                        new MemoryStream(Encoding.UTF8.GetBytes(currentEvent.Data)), cancellationToken: cancellationToken);

                    throw new Exception(res?.Error?.Message);
                }

                if (currentEvent.ContentBlock == null)
                {
                    currentEvent = new SseEvent();
                }
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
        public string EventType { get; set; }
        public string? Data { get; set; }
        public ContentBlock? ContentBlock { get; set; }

        public SseEvent(string eventType, string? data = null, ContentBlock? contentBlock = null)
        {
            EventType = eventType;
            Data = data;
            ContentBlock = contentBlock;
        }
    }

    private class ContentBlock
    {
        [JsonPropertyName("type")]
        public string? Type { get; set; }

        [JsonPropertyName("id")]
        public string? Id { get; set; }

        [JsonPropertyName("name")]
        public string? Name { get; set; }

        [JsonPropertyName("input")]
        public object? Input { get; set; }

        public string? parameters { get; set; }

        public void AppendDeltaParameters(string deltaParams)
        {
            StringBuilder sb = new StringBuilder(parameters);
            sb.Append(deltaParams);
            parameters = sb.ToString();
        }

        public ToolUseContent CreateToolUseContent()
        {
            return new ToolUseContent { Id = Id, Name = Name, Input = parameters };
        }
    }

    private class DataBlock
    {
        [JsonPropertyName("content_block")]
        public ContentBlock? ContentBlock { get; set; }
    }
}
