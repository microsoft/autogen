// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralAgentExtension.cs

using AutoGen.Core;

namespace AutoGen.Mistral.Extension;

public static class MistralAgentExtension
{
    /// <summary>
    /// Register a <see cref="MistralChatMessageConnector"/> to support more AutoGen message types.
    /// </summary>
    public static MiddlewareStreamingAgent<MistralClientAgent> RegisterMessageConnector(
        this MistralClientAgent agent, MistralChatMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new MistralChatMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }

    /// <summary>
    /// Register a <see cref="MistralChatMessageConnector"/> to support more AutoGen message types.
    /// </summary>
    public static MiddlewareStreamingAgent<MistralClientAgent> RegisterMessageConnector(
        this MiddlewareStreamingAgent<MistralClientAgent> agent, MistralChatMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new MistralChatMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }
}
