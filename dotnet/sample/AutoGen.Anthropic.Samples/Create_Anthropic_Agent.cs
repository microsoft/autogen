// Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogen-ai/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// Create_Anthropic_Agent.cs

using AutoGen.Anthropic.Extensions;
using AutoGen.Anthropic.Utils;
using AutoGen.Core;

namespace AutoGen.Anthropic.Samples;

public static class Create_Anthropic_Agent
{
    public static async Task RunAsync()
    {
        #region create_anthropic_agent
        var apiKey = Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY") ?? throw new Exception("Missing ANTHROPIC_API_KEY environment variable.");
        var anthropicClient = new AnthropicClient(new HttpClient(), AnthropicConstants.Endpoint, apiKey);
        var agent = new AnthropicClientAgent(anthropicClient, "assistant", AnthropicConstants.Claude3Haiku);
        #endregion

        #region register_middleware
        var agentWithConnector = agent
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion register_middleware

        await agentWithConnector.SendAsync(new TextMessage(Role.Assistant, "Hello", from: "user"));
    }
}
