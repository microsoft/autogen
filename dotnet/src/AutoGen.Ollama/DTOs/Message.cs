// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatResponseUpdate.cs

using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class Message
{
    public Message()
    {
    }

    public Message(string role, string value)
    {
        Role = role;
        Value = value;
    }

    /// <summary>
    /// the role of the message, either system, user or assistant
    /// </summary>
    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;
    /// <summary>
    /// the content of the message
    /// </summary>
    [JsonPropertyName("content")]
    public string Value { get; set; } = string.Empty;

    /// <summary>
    ///  (optional): a list of images to include in the message (for multimodal models such as llava)
    /// </summary>
    [JsonPropertyName("images")]
    public IList<string>? Images { get; set; }
}
