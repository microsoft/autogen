// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIUserMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "user";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}
