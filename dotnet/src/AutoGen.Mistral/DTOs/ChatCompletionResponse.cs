// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatCompletionResponse.cs

using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

public class ChatCompletionResponse
{
    /// <summary>
    /// Gets or Sets Id
    /// </summary>
    /// <example>cmpl-e5cc70bb28c444948073e77776eb30ef</example>
    [JsonPropertyName("id")]
    public string? Id { get; set; }

    /// <summary>
    /// Gets or Sets VarObject
    /// </summary>
    /// <example>chat.completion</example>
    [JsonPropertyName("object")]
    public string? VarObject { get; set; }

    /// <summary>
    /// Gets or Sets Created
    /// </summary>
    /// <example>1702256327</example>
    [JsonPropertyName("created")]
    public int Created { get; set; }

    /// <summary>
    /// Gets or Sets Model
    /// </summary>
    /// <example>mistral-tiny</example>
    [JsonPropertyName("model")]
    public string? Model { get; set; }

    /// <summary>
    /// Gets or Sets Choices
    /// </summary>
    [JsonPropertyName("choices")]
    public List<Choice>? Choices { get; set; }

    /// <summary>
    /// Gets or Sets Usage
    /// </summary>
    [JsonPropertyName("usage")]
    public Usage? Usage { get; set; }
}
