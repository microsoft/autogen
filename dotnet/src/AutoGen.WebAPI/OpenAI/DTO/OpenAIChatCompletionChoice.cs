// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIChatCompletionChoice.cs

using System.Text.Json.Serialization;

namespace AutoGen.Service.OpenAI.DTO;

internal class OpenAIChatCompletionChoice
{
    [JsonPropertyName("finish_reason")]
    public string? FinishReason { get; set; }

    [JsonPropertyName("index")]
    public int Index { get; set; }

    [JsonPropertyName("message")]
    public OpenAIChatCompletionMessage? Message { get; set; }

    [JsonPropertyName("delta")]
    public OpenAIChatCompletionMessage? Delta { get; set; }
}
