// Copyright (c) Microsoft Corporation. All rights reserved.
// PrintMessageMiddlewareCodeSnippet.cs

using AutoGen.Core;
using AutoGen.OpenAI;
using AutoGen.OpenAI.Extension;

namespace AutoGen.BasicSample.CodeSnippet;

internal class PrintMessageMiddlewareCodeSnippet
{
    public async Task PrintMessageMiddlewareAsync()
    {
        var config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var endpoint = new Uri(config.Endpoint);
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();
        var agent = new OpenAIChatAgent(gpt4o, "assistant", config.DeploymentName)
            .RegisterMessageConnector();

        #region PrintMessageMiddleware
        var agentWithPrintMessageMiddleware = agent
            .RegisterPrintMessage();

        await agentWithPrintMessageMiddleware.SendAsync("write a long poem");
        #endregion PrintMessageMiddleware
    }

    public async Task PrintMessageStreamingMiddlewareAsync()
    {
        var config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var endpoint = new Uri(config.Endpoint);
        var gpt4o = LLMConfiguration.GetOpenAIGPT4o_mini();

        #region print_message_streaming
        var streamingAgent = new OpenAIChatAgent(gpt4o, "assistant")
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        await streamingAgent.SendAsync("write a long poem");
        #endregion print_message_streaming
    }
}
