// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
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
