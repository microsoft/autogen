// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// UserProxyAgent.cs

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen;

public class UserProxyAgent : ConversableAgent
{
    public UserProxyAgent(
        string name,
        string systemMessage = "You are a helpful AI assistant",
        ConversableAgentConfig? llmConfig = null,
        Func<IEnumerable<IMessage>, CancellationToken, Task<bool>>? isTermination = null,
        HumanInputMode humanInputMode = HumanInputMode.ALWAYS,
        IDictionary<string, Func<string, Task<string>>>? functionMap = null,
        string? defaultReply = null)
        : base(name: name,
              systemMessage: systemMessage,
              llmConfig: llmConfig,
              isTermination: isTermination,
              humanInputMode: humanInputMode,
              functionMap: functionMap,
              defaultReply: defaultReply)
    {
    }
}
