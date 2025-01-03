// Copyright (c) Microsoft Corporation. All rights reserved.
// ErrorResponse.cs

using System.Text.Json.Serialization;

namespace AutoGen.Anthropic.DTO;

public sealed class ErrorResponse
{
    [JsonPropertyName("error")]
    public Error? Error { get; set; }
}

public sealed class Error
{
    [JsonPropertyName("Type")]
    public string? Type { get; set; }

    [JsonPropertyName("message")]
    public string? Message { get; set; }
}
