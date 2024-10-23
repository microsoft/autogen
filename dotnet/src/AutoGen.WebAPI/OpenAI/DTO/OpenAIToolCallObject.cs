// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIToolCallObject
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("arguments")]
    public string? Arguments { get; set; }
}
