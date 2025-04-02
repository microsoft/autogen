// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIMessage.cs

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

[JsonConverter(typeof(OpenAIMessageConverter))]
internal abstract class OpenAIMessage
{
    [JsonPropertyName("role")]
    public abstract string? Role { get; }
}
