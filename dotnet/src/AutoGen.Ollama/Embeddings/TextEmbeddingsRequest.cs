// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// TextEmbeddingsRequest.cs

using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class TextEmbeddingsRequest
{
    /// <summary>
    /// name of model to generate embeddings from
    /// </summary>
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;
    /// <summary>
    /// text to generate embeddings for
    /// </summary>
    [JsonPropertyName("prompt")]
    public string Prompt { get; set; } = string.Empty;
    /// <summary>
    /// additional model parameters listed in the documentation for the Modelfile such as temperature
    /// </summary>
    [JsonPropertyName("options")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ModelReplyOptions? Options { get; set; }
    /// <summary>
    ///  controls how long the model will stay loaded into memory following the request (default: 5m)
    /// </summary>
    [JsonPropertyName("keep_alive")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? KeepAlive { get; set; }
}
