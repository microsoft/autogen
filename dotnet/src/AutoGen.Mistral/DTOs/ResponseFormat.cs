// Copyright (c) Microsoft Corporation. All rights reserved.
// ResponseFormat.cs

using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

public class ResponseFormat
{
    [JsonPropertyName("type")]
    public string ResponseFormatType { get; set; } = "json_object";
}
