// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.WebAPI.OpenAI.DTO;

internal class OpenAIStreamOptions
{
    [JsonPropertyName("include_usage")]
    public bool? IncludeUsage { get; set; }
}
