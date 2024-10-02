// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionOption.cs

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIChatCompletionOption
{
    [JsonPropertyName("messages")]
    public OpenAIMessage[]? Messages { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("max_tokens")]
    public int? MaxTokens { get; set; }

    [JsonPropertyName("temperature")]
    public float Temperature { get; set; } = 1;

    /// <summary>
    /// If set, partial message deltas will be sent, like in ChatGPT. Tokens will be sent as data-only server-sent events as they become available, with the stream terminated by a data: [DONE] message
    /// </summary>
    [JsonPropertyName("stream")]
    public bool? Stream { get; set; } = false;

    [JsonPropertyName("stream_options")]
    public OpenAIStreamOptions? StreamOptions { get; set; }

    [JsonPropertyName("stop")]
    public string[]? Stop { get; set; }
}
