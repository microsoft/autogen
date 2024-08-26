// Copyright (c) Microsoft Corporation. All rights reserved.
// PrintMessageMiddlewareCodeSnippet.cs

using AutoGen.Core;
using AutoGen.OpenAI.V1;
using AutoGen.OpenAI.V1.Extension;
using Azure;
using Azure.AI.OpenAI;

namespace AutoGen.BasicSample.CodeSnippet;

internal class PrintMessageMiddlewareCodeSnippet
{
    public async Task PrintMessageMiddlewareAsync()
    {
        var config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var endpoint = new Uri(config.Endpoint);
        var openaiClient = new OpenAIClient(endpoint, new AzureKeyCredential(config.ApiKey));
        var agent = new OpenAIChatAgent(openaiClient, "assistant", config.DeploymentName)
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
        var openaiClient = new OpenAIClient(endpoint, new AzureKeyCredential(config.ApiKey));

        #region print_message_streaming
        var streamingAgent = new OpenAIChatAgent(openaiClient, "assistant", config.DeploymentName)
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        await streamingAgent.SendAsync("write a long poem");
        #endregion print_message_streaming
    }
}
