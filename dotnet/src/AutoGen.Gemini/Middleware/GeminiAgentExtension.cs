// Copyright (c) Microsoft Corporation. All rights reserved.
// GeminiAgentExtension.cs

using AutoGen.Core;

namespace AutoGen.Gemini;

public static class GeminiAgentExtension
{

    /// <summary>
    /// Register an <see cref="GeminiMessageConnector"/> to the <see cref="GeminiChatAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="GeminiMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<GeminiChatAgent> RegisterMessageConnector(
        this GeminiChatAgent agent, GeminiMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new GeminiMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }

    /// <summary>
    /// Register an <see cref="GeminiMessageConnector"/> to the <see cref="MiddlewareAgent{T}"/> where T is <see cref="GeminiChatAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="GeminiMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<GeminiChatAgent> RegisterMessageConnector(
        this MiddlewareStreamingAgent<GeminiChatAgent> agent, GeminiMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new GeminiMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }
}
