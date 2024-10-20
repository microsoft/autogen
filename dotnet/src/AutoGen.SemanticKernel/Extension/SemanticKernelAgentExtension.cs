// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelAgentExtension.cs

namespace AutoGen.SemanticKernel.Extension;

public static class SemanticKernelAgentExtension
{
    /// <summary>
    /// Register an <see cref="SemanticKernelChatMessageContentConnector"/> to the <see cref="SemanticKernelAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="SemanticKernelChatMessageContentConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<SemanticKernelAgent> RegisterMessageConnector(
        this SemanticKernelAgent agent, SemanticKernelChatMessageContentConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new SemanticKernelChatMessageContentConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }

    /// <summary>
    /// Register an <see cref="SemanticKernelChatMessageContentConnector"/> to the <see cref="MiddlewareAgent{T}"/> where T is <see cref="SemanticKernelAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="SemanticKernelChatMessageContentConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<SemanticKernelAgent> RegisterMessageConnector(
        this MiddlewareStreamingAgent<SemanticKernelAgent> agent, SemanticKernelChatMessageContentConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new SemanticKernelChatMessageContentConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }
}
