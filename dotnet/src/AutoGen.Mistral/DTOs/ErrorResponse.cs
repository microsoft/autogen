// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

public class ErrorResponse
{
    public ErrorResponse(Error error)
    {
        Error = error;
    }
    /// <summary>
    /// Gets or Sets Error
    /// </summary>
    [JsonPropertyName("error")]
    public Error Error { get; set; }
}
