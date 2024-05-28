// Copyright (c) Microsoft Corporation. All rights reserved.
// Chat_With_LLaMA.cs

#region Using
using AutoGen.Core;
using AutoGen.Ollama.Extension;
#endregion Using

namespace AutoGen.Ollama.Sample;

public class Chat_With_LLaMA
{
    public static async Task RunAsync()
    {
        #region Create_Ollama_Agent
        using var httpClient = new HttpClient()
        {
            BaseAddress = new Uri("http://localhost:11434"),
        };

        var ollamaAgent = new OllamaAgent(
            httpClient: httpClient,
            name: "ollama",
            modelName: "llama3:latest",
            systemMessage: "You are a helpful AI assistant")
            .RegisterMessageConnector()
            .RegisterPrintMessage();

        var reply = await ollamaAgent.SendAsync("Can you write a piece of C# code to calculate 100th of fibonacci?");
        #endregion Create_Ollama_Agent
    }
}
