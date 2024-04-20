// Copyright (c) Microsoft Corporation. All rights reserved.
// MistralAgentExtension.cs

using AutoGen.Core;

namespace AutoGen.Mistral.Extension;

public static class MistralAgentExtension
{
    public static MiddlewareStreamingAgent<MistralClientAgent> RegisterMessageConnector(
        this MistralClientAgent agent, MistralChatMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new MistralChatMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector)
                    .RegisterMiddleware(connector);

    }

    public static MiddlewareStreamingAgent<MistralClientAgent> RegisterMessageConnector(
        this MiddlewareStreamingAgent<MistralClientAgent> agent, MistralChatMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new MistralChatMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector)
                    .RegisterMiddleware(connector);
    }
}
