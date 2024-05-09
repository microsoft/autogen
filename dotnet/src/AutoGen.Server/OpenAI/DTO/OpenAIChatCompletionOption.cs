// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionOption.cs

using System.Text.Json.Serialization;

namespace AutoGen.Service.OpenAI.DTO;

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
}
