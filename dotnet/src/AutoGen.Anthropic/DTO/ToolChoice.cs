// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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
