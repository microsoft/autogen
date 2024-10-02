// Copyright (c) Microsoft Corporation. All rights reserved.
// Connect_To_Azure_OpenAI.cs

#region using_statement
using AutoGen.Core;
using AutoGen.OpenAI.Extension;
using Azure;
using Azure.AI.OpenAI;
#endregion using_statement

namespace AutoGen.OpenAI.Sample;

public class Connect_To_Azure_OpenAI
{
    public static async Task RunAsync()
    {
        #region create_agent
        var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY") ?? throw new InvalidOperationException("Please set environment variable AZURE_OPENAI_API_KEY");
        var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT") ?? throw new InvalidOperationException("Please set environment variable AZURE_OPENAI_ENDPOINT");
        var model = Environment.GetEnvironmentVariable("AZURE_OPENAI_DEPLOY_NAME") ?? "gpt-4o-mini";

        // Use AzureOpenAIClient to connect to openai model deployed on azure.
        // The AzureOpenAIClient comes from Azure.AI.OpenAI package
        var openAIClient = new AzureOpenAIClient(new Uri(endpoint), new AzureKeyCredential(apiKey));

        var agent = new OpenAIChatAgent(
            chatClient: openAIClient.GetChatClient(model),
            name: "assistant",
            systemMessage: "You are a helpful assistant designed to output JSON.",
            seed: 0)
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion create_agent

        #region send_message
        await agent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
        #endregion send_message
    }
}
