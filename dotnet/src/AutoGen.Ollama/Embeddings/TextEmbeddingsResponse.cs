// Copyright (c) Microsoft Corporation. All rights reserved.
// TextEmbeddingsResponse.cs

using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class TextEmbeddingsResponse
{
    [JsonPropertyName("embedding")]
    public double[]? Embedding { get; set; }
}
