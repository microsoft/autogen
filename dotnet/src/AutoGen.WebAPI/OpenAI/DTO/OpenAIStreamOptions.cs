// Copyright (c) Microsoft Corporation. All rights reserved.
//

using System.Text.Json.Serialization;

namespace AutoGen.Service.OpenAI.DTO;

internal class OpenAIStreamOptions
{
    [JsonPropertyName("include_usage")]
    public bool? IncludeUsage { get; set; }
}
