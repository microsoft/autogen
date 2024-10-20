// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// OllamaAgentExtension.cs

using AutoGen.Core;

namespace AutoGen.Ollama.Extension;

public static class OllamaAgentExtension
{
    /// <summary>
    /// Register an <see cref="OllamaMessageConnector"/> to the <see cref="OllamaAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="OllamaMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<OllamaAgent> RegisterMessageConnector(
        this OllamaAgent agent, OllamaMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new OllamaMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }

    /// <summary>
    /// Register an <see cref="OllamaMessageConnector"/> to the <see cref="MiddlewareAgent{T}"/> where T is <see cref="OllamaAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="OllamaMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<OllamaAgent> RegisterMessageConnector(
        this MiddlewareStreamingAgent<OllamaAgent> agent, OllamaMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new OllamaMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }
}
