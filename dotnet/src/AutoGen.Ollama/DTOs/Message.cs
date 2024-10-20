// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// Message.cs

using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace AutoGen.Ollama;

public class Message
{
    public Message()
    {
    }

    public Message(string role, string value)
    {
        Role = role;
        Value = value;
    }

    /// <summary>
    /// the role of the message, either system, user or assistant
    /// </summary>
    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;
    /// <summary>
    /// the content of the message
    /// </summary>
    [JsonPropertyName("content")]
    public string Value { get; set; } = string.Empty;

    /// <summary>
    ///  (optional): a list of images to include in the message (for multimodal models such as llava)
    /// </summary>
    [JsonPropertyName("images")]
    public IList<string>? Images { get; set; }
}
