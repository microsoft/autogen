// Copyright (c) Microsoft Corporation. All rights reserved.
// AnthropicAgentExtension.cs

using AutoGen.Anthropic.Middleware;
using AutoGen.Core;

namespace AutoGen.Anthropic.Extensions;

public static class AnthropicAgentExtension
{
    /// <summary>
    /// Register an <see cref="AnthropicMessageConnector"/> to the <see cref="AnthropicClientAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="AnthropicMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<AnthropicClientAgent> RegisterMessageConnector(
        this AnthropicClientAgent agent, AnthropicMessageConnector? connector = null)
    {
        connector ??= new AnthropicMessageConnector();

        return agent.RegisterStreamingMiddleware(connector);
    }

    /// <summary>
    /// Register an <see cref="AnthropicMessageConnector"/> to the <see cref="MiddlewareAgent{T}"/> where T is <see cref="AnthropicClientAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="AnthropicMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<AnthropicClientAgent> RegisterMessageConnector(
        this MiddlewareStreamingAgent<AnthropicClientAgent> agent, AnthropicMessageConnector? connector = null)
    {
        connector ??= new AnthropicMessageConnector();

        return agent.RegisterStreamingMiddleware(connector);
    }
}
