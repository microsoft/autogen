// Copyright (c) Microsoft Corporation. All rights reserved.
// Usage.cs

using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

public class Usage
{
    [JsonPropertyName("prompt_tokens")]
    public int PromptTokens { get; set; }

    /// <summary>
    /// Gets or Sets CompletionTokens
    /// </summary>
    /// <example>93</example>
    [JsonPropertyName("completion_tokens")]
    public int CompletionTokens { get; set; }

    /// <summary>
    /// Gets or Sets TotalTokens
    /// </summary>
    /// <example>107</example>
    [JsonPropertyName("total_tokens")]
    public int TotalTokens { get; set; }
}
