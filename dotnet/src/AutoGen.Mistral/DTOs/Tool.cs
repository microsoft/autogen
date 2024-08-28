// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// Tool.cs

using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

public abstract class ToolBase
{
    [JsonPropertyName("type")]
    public string Type { get; set; }

    public ToolBase(string type)
    {
        Type = type;
    }
}

public class FunctionTool : ToolBase
{
    public FunctionTool(FunctionDefinition function)
        : base("function")
    {
        Function = function;
    }

    [JsonPropertyName("function")]
    public FunctionDefinition Function { get; set; }
}

[JsonConverter(typeof(JsonPropertyNameEnumConverter<ToolChoiceEnum>))]
public enum ToolChoiceEnum
{
    /// <summary>
    /// Auto-detect whether to call a function.
    /// </summary>
    [JsonPropertyName("auto")]
    Auto = 0,

    /// <summary>
    /// Won't call a function.
    /// </summary>
    [JsonPropertyName("none")]
    None,

    /// <summary>
    /// Force to call a function.
    /// </summary>
    [JsonPropertyName("any")]
    Any,
}
