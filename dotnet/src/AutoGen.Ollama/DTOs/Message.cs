// Copyright (c) Microsoft Corporation. All rights reserved.
// Message.cs

using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class Message
{
    public Message()
    {
    }

    public Message(string role, string? value = null)
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
    public string? Value { get; set; }

    /// <summary>
    ///  (optional): a list of images to include in the message (for multimodal models such as llava)
    /// </summary>
    [JsonPropertyName("images")]
    public IList<string>? Images { get; set; }

    /// <summary>
    /// A list of tools the model wants to use. Not all models currently support tools.
    /// Tool call is not supported while streaming.
    /// </summary>
    [JsonPropertyName("tool_calls")]
    public IEnumerable<ToolCall>? ToolCalls { get; set; }

    public class ToolCall
    {
        [JsonPropertyName("function")]
        public Function? Function { get; set; }
    }

    public class Function
    {
        [JsonPropertyName("name")]
        public string? Name { get; set; }

        [JsonPropertyName("arguments")]
        public Dictionary<string, string>? Arguments { get; set; }
    }
}

