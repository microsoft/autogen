// Copyright (c) Microsoft Corporation. All rights reserved.
// GenerateContentRequest.cs

using System.Text.Json.Serialization;

namespace AutoGen.Gemini.DTO.V1Beta;

internal class GenerateContentRequest
{
    [JsonPropertyName("contents")]
    public Content[] Contents { get; set; } = null!;
}

internal class Content
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = null!;

    [JsonPropertyName("parts")]
    public Part[] Parts { get; set; } = null!;
}

internal abstract class Part
{
}

internal class TextPart : Part
{
    [JsonPropertyName("data")]
    public string Data { get; set; } = null!;
}

internal class InlinePart : Part
{
    [JsonPropertyName("data")]
    public Blob Data { get; set; } = null!;

    internal class Blob
    {
        [JsonPropertyName("mimeType")]
        public string MimeType { get; set; } = null!;

        [JsonPropertyName("data")]
        public string Data { get; set; } = null!;
    }
}
