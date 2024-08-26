// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// Choice.cs

using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

public class Choice
{
    [JsonConverter(typeof(JsonPropertyNameEnumConverter<FinishReasonEnum>))]
    public enum FinishReasonEnum
    {
        /// <summary>
        /// Enum Stop for value: stop
        /// </summary>
        [JsonPropertyName("stop")]
        Stop = 1,

        /// <summary>
        /// Enum Length for value: length
        /// </summary>
        [JsonPropertyName("length")]
        Length = 2,

        /// <summary>
        /// Enum ModelLength for value: model_length
        /// </summary>
        [JsonPropertyName("model_length")]
        ModelLength = 3,

        [JsonPropertyName("error")]
        Error = 4,

        [JsonPropertyName("tool_calls")]
        ToolCalls = 5,
    }

    /// <summary>
    /// Gets or Sets FinishReason
    /// </summary>
    [JsonPropertyName("finish_reason")]
    public FinishReasonEnum? FinishReason { get; set; }

    [JsonPropertyName("index")]
    public int Index { get; set; }

    /// <summary>
    /// Gets or Sets Message
    /// </summary>
    [JsonPropertyName("message")]
    public ChatMessage? Message { get; set; }

    /// <summary>
    /// Gets or Sets Delta
    /// </summary>
    [JsonPropertyName("delta")]
    public ChatMessage? Delta { get; set; }
}
