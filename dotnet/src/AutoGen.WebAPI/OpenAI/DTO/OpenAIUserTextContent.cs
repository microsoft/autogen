// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIUserTextContent : OpenAIUserMessageItem
{
    [JsonPropertyName("type")]
    public override string MessageType { get; } = "text";

    [JsonPropertyName("text")]
    public string? Content { get; set; }
}
