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
