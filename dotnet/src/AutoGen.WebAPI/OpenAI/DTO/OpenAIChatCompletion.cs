// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletion.cs

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIChatCompletion
{
    [JsonPropertyName("id")]
    public string? ID { get; set; }

    [JsonPropertyName("created")]
    public long Created { get; set; }

    [JsonPropertyName("choices")]
    public OpenAIChatCompletionChoice[]? Choices { get; set; }

    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("system_fingerprint")]
    public string? SystemFingerprint { get; set; }

    [JsonPropertyName("object")]
    public string Object { get; set; } = "chat.completion";

    [JsonPropertyName("usage")]
    public OpenAIChatCompletionUsage? Usage { get; set; }
}
