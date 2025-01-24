// Copyright (c) Microsoft Corporation. All rights reserved.
// ToolChoice.cs

using System.Text.Json.Serialization;
using AutoGen.Anthropic.Converters;

namespace AutoGen.Anthropic.DTO;

[JsonConverter(typeof(JsonPropertyNameEnumConverter<ToolChoiceType>))]
public enum ToolChoiceType
{
    [JsonPropertyName("auto")]
    Auto, // Default behavior

    [JsonPropertyName("any")]
    Any, // Use any provided tool

    [JsonPropertyName("tool")]
    Tool // Force a specific tool
}

public class ToolChoice
{
    [JsonPropertyName("type")]
    public ToolChoiceType Type { get; set; }

    [JsonPropertyName("name")]
    public string? Name { get; set; }

    private ToolChoice(ToolChoiceType type, string? name = null)
    {
        Type = type;
        Name = name;
    }

    public static ToolChoice Auto => new(ToolChoiceType.Auto);
    public static ToolChoice Any => new(ToolChoiceType.Any);
    public static ToolChoice ToolUse(string name) => new(ToolChoiceType.Tool, name);
}
