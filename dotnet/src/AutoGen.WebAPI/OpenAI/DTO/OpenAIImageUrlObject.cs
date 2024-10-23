// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIImageUrlObject
{
    [JsonPropertyName("url")]
    public string? Url { get; set; }

    [JsonPropertyName("detail")]
    public string? Detail { get; set; } = "auto";
}
