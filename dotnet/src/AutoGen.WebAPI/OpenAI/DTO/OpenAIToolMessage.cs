// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIToolMessage.cs

using System.Text.Json.Serialization;

namespace AutoGen.Service.OpenAI.DTO;

internal class OpenAIToolMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "tool";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("tool_call_id")]
    public string? ToolCallId { get; set; }
}
