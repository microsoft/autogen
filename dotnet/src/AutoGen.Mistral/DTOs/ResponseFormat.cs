// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

public class ResponseFormat
{
    [JsonPropertyName("type")]
    public string ResponseFormatType { get; set; } = "json_object";
}
