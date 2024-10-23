// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIUserImageContent : OpenAIUserMessageItem
{
    [JsonPropertyName("type")]
    public override string MessageType { get; } = "image";

    [JsonPropertyName("image_url")]
    public string? Url { get; set; }
}
