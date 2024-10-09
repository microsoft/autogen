// Copyright (c) Microsoft Corporation. All rights reserved.
// Connect_To_Ollama.cs

#region using_statement
using AutoGen.Core;
using AutoGen.OpenAI.Extension;
using OpenAI;
#endregion using_statement

namespace AutoGen.OpenAI.Sample;

public class Connect_To_Ollama
{
    public static async Task RunAsync()
    {
        #region create_agent
        // api-key is not required for local server
        // so you can use any string here
        var openAIClient = new OpenAIClient("api-key", new OpenAIClientOptions
        {
            Endpoint = new Uri("http://localhost:11434/v1/"), // remember to add /v1/ at the end to connect to Ollama openai server
        });
        var model = "llama3";

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
