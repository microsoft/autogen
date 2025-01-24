// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatCompletionResponse.cs

using System.Text.Json.Serialization;

namespace AutoGen.Anthropic.DTO;

public class ChatCompletionResponse
{
    [JsonPropertyName("content")]
    public List<ContentBase>? Content { get; set; }

    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("role")]
    public string? Role { get; set; }

    [JsonPropertyName("stop_reason")]
    public string? StopReason { get; set; }

    [JsonPropertyName("stop_sequence")]
    public object? StopSequence { get; set; }

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("usage")]
    public Usage? Usage { get; set; }

    [JsonPropertyName("delta")]
    public Delta? Delta { get; set; }

    [JsonPropertyName("message")]
    public StreamingMessage? StreamingMessage { get; set; }
}

public class StreamingMessage
{
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("role")]
    public string? Role { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("stop_reason")]
    public object? StopReason { get; set; }

    [JsonPropertyName("stop_sequence")]
    public object? StopSequence { get; set; }

    [JsonPropertyName("usage")]
    public Usage? Usage { get; set; }
}

public class Usage
{
    [JsonPropertyName("input_tokens")]
    public int InputTokens { get; set; }

    [JsonPropertyName("output_tokens")]
    public int OutputTokens { get; set; }

    [JsonPropertyName("cache_creation_input_tokens")]
    public int CacheCreationInputTokens { get; set; }

    [JsonPropertyName("cache_read_input_tokens")]
    public int CacheReadInputTokens { get; set; }
}

public class Delta
{
    [JsonPropertyName("stop_reason")]
    public string? StopReason { get; set; }

    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("text")]
    public string? Text { get; set; }

    [JsonPropertyName("partial_json")]
    public string? PartialJson { get; set; }

    [JsonPropertyName("usage")]
    public Usage? Usage { get; set; }
}
