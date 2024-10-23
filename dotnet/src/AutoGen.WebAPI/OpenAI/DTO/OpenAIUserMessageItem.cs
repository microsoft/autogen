// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal abstract class OpenAIUserMessageItem
{
    [JsonPropertyName("type")]
    public abstract string MessageType { get; }
}
