// Copyright (c) Microsoft Corporation. All rights reserved.
// Connect_To_OpenAI_o1_preview.cs

using AutoGen.Core;
using OpenAI;

namespace AutoGen.OpenAI.Sample;

public class Connect_To_OpenAI_o1_preview
{
    public static async Task RunAsync()
    {
        #region create_agent
        var apiKey = Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? throw new InvalidOperationException("Please set environment variable OPENAI_API_KEY");
        var openAIClient = new OpenAIClient(apiKey);

        // until 2024/09/12
        // openai o1-preview doesn't support systemMessage, temperature, maxTokens, streaming output
        // so in order to use OpenAIChatAgent with o1-preview, you need to set those parameters to null
        var agent = new OpenAIChatAgent(
            chatClient: openAIClient.GetChatClient("o1-preview"),
            name: "assistant",
            systemMessage: null,
            temperature: null,
            maxTokens: null,
            seed: 0)
            // by using RegisterMiddleware instead of RegisterStreamingMiddleware
            // it turns an IStreamingAgent into an IAgent and disables streaming
            .RegisterMiddleware(new OpenAIChatRequestMessageConnector())
            .RegisterPrintMessage();
        #endregion create_agent

        #region send_message
        await agent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
        #endregion send_message
    }
}
