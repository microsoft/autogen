// Copyright (c) Microsoft Corporation. All rights reserved.
// Connect_To_Tuning_Engines.cs

#region using_statement
using System.ClientModel;
using AutoGen.Core;
using AutoGen.OpenAI.Extension;
using OpenAI;
#endregion using_statement

namespace AutoGen.OpenAI.Sample;

public class Connect_To_Tuning_Engines
{
    public static async Task RunAsync()
    {
        #region create_agent
        var apiKey = Environment.GetEnvironmentVariable("TUNING_ENGINES_API_KEY")
            ?? throw new InvalidOperationException("TUNING_ENGINES_API_KEY is not set.");
        var model = Environment.GetEnvironmentVariable("TUNING_ENGINES_MODEL") ?? "your-model-alias";

        var openAIClient = new OpenAIClient(new ApiKeyCredential(apiKey), new OpenAIClientOptions
        {
            Endpoint = new Uri("https://api.tuningengines.com/v1/"),
        });

        var agent = new OpenAIChatAgent(
            chatClient: openAIClient.GetChatClient(model),
            name: "assistant",
            systemMessage: "You are a helpful assistant.",
            seed: 0)
            .RegisterMessageConnector()
            .RegisterPrintMessage();
        #endregion create_agent

        #region send_message
        await agent.SendAsync("Can you explain how governed model access helps production agent systems?");
        #endregion send_message
    }
}
