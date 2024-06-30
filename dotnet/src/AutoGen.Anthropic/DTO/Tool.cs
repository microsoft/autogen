// Copyright (c) Microsoft Corporation. All rights reserved.
// Tool.cs

using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace AutoGen.Anthropic.DTO;

public class Tool
{
    [JsonPropertyName("name")]
    public string? Name { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("input_schema")]
    public InputSchema? InputSchema { get; set; }
}

public class InputSchema
{
    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("properties")]
    public Dictionary<string, SchemaProperty>? Properties { get; set; }

    [JsonPropertyName("required")]
    public List<string>? Required { get; set; }
}

public class SchemaProperty
{
    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }
}
