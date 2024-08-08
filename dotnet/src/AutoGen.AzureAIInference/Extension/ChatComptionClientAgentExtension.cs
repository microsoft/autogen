// Copyright (c) Microsoft Corporation. All rights reserved.
// OpenAIAgentExtension.cs

using AutoGen.Core;

namespace AutoGen.AzureAIInference.Extension;

public static class ChatComptionClientAgentExtension
{
    /// <summary>
    /// Register an <see cref="AzureAIInferenceChatRequestMessageConnector"/> to the <see cref="ChatCompletionClientAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="AzureAIInferenceChatRequestMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<ChatCompletionClientAgent> RegisterMessageConnector(
        this ChatCompletionClientAgent agent, AzureAIInferenceChatRequestMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new AzureAIInferenceChatRequestMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }

    /// <summary>
    /// Register an <see cref="AzureAIInferenceChatRequestMessageConnector"/> to the <see cref="MiddlewareAgent{T}"/> where T is <see cref="ChatCompletionClientAgent"/>
    /// </summary>
    /// <param name="connector">the connector to use. If null, a new instance of <see cref="AzureAIInferenceChatRequestMessageConnector"/> will be created.</param>
    public static MiddlewareStreamingAgent<ChatCompletionClientAgent> RegisterMessageConnector(
        this MiddlewareStreamingAgent<ChatCompletionClientAgent> agent, AzureAIInferenceChatRequestMessageConnector? connector = null)
    {
        if (connector == null)
        {
            connector = new AzureAIInferenceChatRequestMessageConnector();
        }

        return agent.RegisterStreamingMiddleware(connector);
    }
}
