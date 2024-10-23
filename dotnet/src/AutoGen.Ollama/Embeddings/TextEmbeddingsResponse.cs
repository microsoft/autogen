// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class TextEmbeddingsResponse
{
    [JsonPropertyName("embedding")]
    public double[]? Embedding { get; set; }
}
