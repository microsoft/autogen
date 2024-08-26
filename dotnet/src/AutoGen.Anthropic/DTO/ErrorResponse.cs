// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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
