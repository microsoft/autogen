// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAISystemMessage.cs

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAISystemMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "system";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}
