// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIToolMessage : OpenAIMessage
{
    [JsonPropertyName("role")]
    public override string? Role { get; } = "tool";

    [JsonPropertyName("content")]
    public string? Content { get; set; }

    [JsonPropertyName("tool_call_id")]
    public string? ToolCallId { get; set; }
}
