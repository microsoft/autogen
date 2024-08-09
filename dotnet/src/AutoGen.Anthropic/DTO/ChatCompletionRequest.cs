// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatCompletionRequest.cs
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace AutoGen.Anthropic.DTO;

public class ChatCompletionRequest
{
    [JsonPropertyName("model")]
    public string? Model { get; set; }

    [JsonPropertyName("messages")]
    public List<ChatMessage> Messages { get; set; }

    [JsonPropertyName("system")]
    public string? SystemMessage { get; set; }

    [JsonPropertyName("max_tokens")]
    public int MaxTokens { get; set; }

    [JsonPropertyName("metadata")]
    public object? Metadata { get; set; }

    [JsonPropertyName("stop_sequences")]
    public string[]? StopSequences { get; set; }

    [JsonPropertyName("stream")]
    public bool? Stream { get; set; }

    [JsonPropertyName("temperature")]
    public decimal? Temperature { get; set; }

    [JsonPropertyName("top_k")]
    public int? TopK { get; set; }

    [JsonPropertyName("top_p")]
    public decimal? TopP { get; set; }

    [JsonPropertyName("tools")]
    public List<Tool>? Tools { get; set; }

    [JsonPropertyName("tool_choice")]
    public ToolChoice? ToolChoice { get; set; }

    public ChatCompletionRequest()
    {
        Messages = new List<ChatMessage>();
    }
}

public class ChatMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; }

    [JsonPropertyName("content")]
    public List<ContentBase> Content { get; set; }

    public ChatMessage(string role, string content)
    {
        Role = role;
        Content = new List<ContentBase>() { new TextContent { Text = content } };
    }

    public ChatMessage(string role, List<ContentBase> content)
    {
        Role = role;
        Content = content;
    }

    public void AddContent(ContentBase content) => Content.Add(content);
}
