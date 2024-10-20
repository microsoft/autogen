// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// ChatComptionClientAgentExtension.cs

using AutoGen.Core;

namespace AutoGen.AzureAIInference.Extension;

public static class ChatComptionClientAgentExtension
{
    /// <summary>
    /// Register an <see cref="AzureAIInferenceChatRequestMessageConnector"/> to the <see cref="ChatCompletionsClientAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="AzureAIInferenceChatRequestMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<ChatCompletionsClientAgent> RegisterMessageConnector(
        this ChatCompletionsClientAgent agent, AzureAIInferenceChatRequestMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new AzureAIInferenceChatRequestMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }

    /// <summary>
    /// Register an <see cref="AzureAIInferenceChatRequestMessageConnector"/> to the <see cref="MiddlewareAgent{T}"/> where T is <see cref="ChatCompletionsClientAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="AzureAIInferenceChatRequestMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<ChatCompletionsClientAgent> RegisterMessageConnector(
        this MiddlewareStreamingAgent<ChatCompletionsClientAgent> agent, AzureAIInferenceChatRequestMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new AzureAIInferenceChatRequestMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }
}
