// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIUserMultiModalMessage.cs

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIUserMultiModalMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "user";

    [JsonPropertyName("content")]
    public OpenAIUserMessageItem[]? Content { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }
}
