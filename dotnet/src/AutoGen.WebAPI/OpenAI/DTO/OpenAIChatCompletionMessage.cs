// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionMessage.cs

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIChatCompletionMessage
{
    [JsonPropertyName("role")]
    public string Role { get; } = "assistant";

    [JsonPropertyName("content")]
    public string? Content { get; set; }
}
