// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

[JsonConverter(typeof(OpenAIMessageConverter))]
internal abstract class OpenAIMessage
{
    [JsonPropertyName("role")]
    public abstract string? Role { get; }
}
