// Copyright (c) Microsoft Corporation. All rights reserved.
// Content.cs

using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace AutoGen.Anthropic.DTO;

public abstract class ContentBase
{
    [JsonPropertyName("type")]
    public abstract string Type { get; }
}

public class TextContent : ContentBase
{
    [JsonPropertyName("type")]
    public override string Type => "text";

    [JsonPropertyName("text")]
    public string? Text { get; set; }
}

public class ImageContent : ContentBase
{
    [JsonPropertyName("type")]
    public override string Type => "image";

    [JsonPropertyName("source")]
    public ImageSource? Source { get; set; }
}

public class ImageSource
{
    [JsonPropertyName("type")]
    public string Type => "base64";

    [JsonPropertyName("media_type")]
    public string? MediaType { get; set; }

    [JsonPropertyName("data")]
    public string? Data { get; set; }
}

public class ToolUseContent : ContentBase
{
    [JsonPropertyName("type")]
    public override string Type => "tool_use";

    [JsonPropertyName("id")]
    public string? Id { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("input")]
    public JsonNode? Input { get; set; }
}

public class ToolResultContent : ContentBase
{
    [JsonPropertyName("type")]
    public override string Type => "tool_result";

    [JsonPropertyName("tool_use_id")]
    public string? Id { get; set; }

    [JsonPropertyName("content")]
    public string? Content { get; set; }
}
