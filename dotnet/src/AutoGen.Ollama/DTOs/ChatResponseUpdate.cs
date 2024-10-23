// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class ChatResponseUpdate
{
    [JsonPropertyName("model")]
    public string Model { get; set; } = string.Empty;

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; set; } = string.Empty;

    [JsonPropertyName("message")]
    public Message? Message { get; set; }

    [JsonPropertyName("done")]
    public bool Done { get; set; }
}
