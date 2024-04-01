// Copyright (c) Microsoft Corporation. All rights reserved.
// PrintMessageMiddlewareCodeSnippet.cs

using AutoGen.Core;
using AutoGen.OpenAI;
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
        var openaiMessageConnector = new OpenAIChatRequestMessageConnector();
        var agent = new OpenAIChatAgent(openaiClient, "assistant", config.DeploymentName)
            .RegisterMiddleware(openaiMessageConnector);

        #region PrintMessageMiddleware
        var agentWithPrintMessageMiddleware = agent
            .RegisterPrintFormatMessageHook();

        await agentWithPrintMessageMiddleware.SendAsync("write a long poem");
        #endregion PrintMessageMiddleware
    }

    public async Task PrintMessageStreamingMiddlewareAsync()
    {
        var config = LLMConfiguration.GetAzureOpenAIGPT3_5_Turbo();
        var endpoint = new Uri(config.Endpoint);
        var openaiClient = new OpenAIClient(endpoint, new AzureKeyCredential(config.ApiKey));
        var openaiMessageConnector = new OpenAIChatRequestMessageConnector();

        #region print_message_streaming
        var streamingAgent = new OpenAIChatAgent(openaiClient, "assistant", config.DeploymentName)
            .RegisterStreamingMiddleware(openaiMessageConnector)
            .RegisterMiddleware(openaiMessageConnector)
            .RegisterPrintFormatMessageHook();

        await streamingAgent.SendAsync("write a long poem");
        #endregion print_message_streaming
    }
}
